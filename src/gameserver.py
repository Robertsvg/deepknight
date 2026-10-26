"""Gameserver-Anbindung fuer den Contest (gspy / Gameserver25).

Verbindet unsere AdvancedAI mit dem offiziellen TU-Berlin-Gameserver
(https://git.tu-berlin.de/programmierpraktikum/Gameserver25).

Protokoll (zeilenbasiert ueber TCP, Default Port 5000, je Nachricht "\n"):

  Handshake/Login
    -> gspy            <- ok
    -> register        <- <uuid-token>
    -> login <uuid>    <- ok

  Lobby
    Host:    -> create <name>            <- ok
             -> set game.type tablut     <- ok
             -> set max_players 2        <- ok
             -> set min_players 2        <- ok
    Joiner:  -> join <name>              <- ok

  Spielstart
    Host sendet wiederholt -> start  bis  <- queued
    Joiner empfaengt bis             <- queued
    beide: <- config ... <- ok  -> ok
    dann:  <- start  (wir sind Spieler 0 = SCHWARZ, ziehen zuerst)
       oder <- wait   (wir sind Spieler 1 = WEISS, ziehen als zweite)

  Spielschleife (bis <- over)
    <- move r,c,r,c  Gegnerzug  -> auf Brett anwenden, eigenen Zug berechnen+senden
    <- time <rest>   unser Restzeit-Konto nach eigenem Zug
    <- over          Spielende

Wichtig: Der Server schickt NICHT das ganze Brett. Wir pflegen unser eigenes
`Board` (Startaufstellung identisch zum Server) und wenden jeden Zug -- eigene
wie gegnerische -- mit `apply_move` an. Das Tablut-Zugformat des Servers
("r1,c1,r2,c2", 0-indiziert) ist exakt unser internes Move-Tupel.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Optional

from src.ai import AdvancedAI
from src.board import BLACK, WHITE, Board, setup_initial_position
from src.evaluation import game_phase
from src.moves import generate_legal_moves
from src.server_rules import apply_move_server_faithful

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000

# Dynamisches Zeitbudget: pro Spielphase ein Faktor auf das neutrale Budget.
# Eroeffnung ist Standardtheorie -> weniger denken; Mittelspiel entscheidet die
# Partie -> am meisten denken; Endspiel (Koenigsflucht/-jagd) braucht wieder
# solide Rechenzeit. Werte contest-erprobt.
_PHASE_BUDGET = {"opening": 0.6, "midgame": 1.5, "endgame": 1.2}

Move = tuple[int, int, int, int]

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gameserver")


def move_to_server(move: Move) -> str:
    """(from_row, from_col, to_row, to_col) -> 'r1,c1,r2,c2'."""
    return ",".join(str(x) for x in move)


def move_from_server(arg: str) -> Move:
    """'r1,c1,r2,c2' -> (from_row, from_col, to_row, to_col)."""
    parts = [int(x) for x in arg.split(",")]
    if len(parts) != 4:
        raise ValueError(f"ungueltiges Zugformat vom Server: {arg!r}")
    return (parts[0], parts[1], parts[2], parts[3])


class TablutServerClient:
    """Async-TCP-Client, der die AdvancedAI am Gameserver spielen laesst."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        per_move_time_s: float = 1.0,
        username: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.per_move_time_s = per_move_time_s
        self.username = username

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

        self.board: Board = Board()
        setup_initial_position(self.board)
        self.our_side: Optional[int] = None
        self.time_remaining: Optional[float] = None
        self.ai = AdvancedAI(time_limit_s=per_move_time_s)
        # Stellungs-Zaehler fuer Wiederholungs-Vermeidung. Key = Board
        # (hashbar ueber attackers/defenders/king/side_to_move/king_left_throne).
        self.seen: dict = {}
        self._record_position(self.board)

    # --- Low-Level-IO ------------------------------------------------------
    async def send(self, msg: str) -> None:
        assert self.writer is not None
        log.info(f"  -> {msg}")
        self.writer.write((msg + "\n").encode())
        await self.writer.drain()

    async def recv(self, timeout: Optional[float] = 30.0) -> str:
        assert self.reader is not None
        raw = await asyncio.wait_for(self.reader.readuntil(b"\n"), timeout)
        msg = raw.decode().strip()
        log.info(f"  <- {msg}")
        return msg

    async def expect_ok(self, what: str) -> None:
        r = await self.recv()
        if r != "ok":
            raise RuntimeError(f"{what}: erwartet 'ok', bekam {r!r}")

    # --- Handshake / Login -------------------------------------------------
    async def _handshake(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await self.send("gspy")
        await self.expect_ok("handshake")

        await self.send("register")
        token = await self.recv()  # uuid-token
        await self.send(f"login {token}")
        await self.expect_ok("login")

        if self.username:
            await self.send(f"username {self.username}")
            await self.expect_ok("username")

    # --- Lobby -------------------------------------------------------------
    async def connect_as_host(
        self, lobby: str, start_pos: str = "", time_account: float = 300.0
    ) -> None:
        await self._handshake()
        await self.send(f"create {lobby}")
        await self.expect_ok("create")
        await self.send("set game.type tablut")
        await self.expect_ok("set game.type")
        await self.send("set max_players 2")
        await self.expect_ok("set max_players")
        await self.send("set min_players 2")
        await self.expect_ok("set min_players")
        # Deterministische Farb-Zuteilung: Der Default-Scheduler "random" wuerfelt
        # die Spielerreihenfolge (und damit Schwarz/Weiss) pro Partie aus.
        # round_robin behaelt die Lobby-Reihenfolge bei -> der HOST ist Spieler 0
        # = SCHWARZ (Angreifer), der Joiner Spieler 1 = WEISS (Verteidiger).
        # So sind die Seiten planbar: hosten = wir Schwarz, beitreten = wir Weiss.
        await self.send("set scheduler round_robin")
        await self.expect_ok("set scheduler")
        # Grosszuegiges Zeitkonto pro Spieler, damit die Partie bis zum echten
        # Ende laeuft statt nach ~30 Zuegen auf Zeit zu enden (Default 60s).
        await self.send(f"set game.time_account {time_account}")
        await self.expect_ok("set game.time_account")
        if start_pos:
            await self.send(f"set game.start_pos {start_pos}")
            await self.expect_ok("set game.start_pos")
        log.info(f"Lobby '{lobby}' erstellt (Tablut, 2 Spieler). Warte auf Gegner...")

    async def connect_and_join(self, lobby: str) -> None:
        await self._handshake()
        await self.send(f"join {lobby}")
        await self.expect_ok("join")
        log.info(f"Lobby '{lobby}' beigetreten.")

    # --- Spielablauf -------------------------------------------------------
    async def _await_queued_as_host(self) -> None:
        # Host stoesst den Spielstart an, sobald die Lobby 'ready' ist.
        while True:
            await self.send("start")
            msg = await self.recv(timeout=None)
            if msg == "queued":
                return
            if msg.startswith("err"):
                # noch nicht genug Spieler -> kurz warten und erneut versuchen
                await asyncio.sleep(0.5)
                continue
            raise RuntimeError(f"start: unerwartete Antwort {msg!r}")

    async def _await_queued_as_joiner(self) -> None:
        while True:
            msg = await self.recv(timeout=None)
            if msg == "queued":
                return

    async def _config_phase(self) -> None:
        # <- config, dann beliebig viele 'set k v', abgeschlossen mit <- ok.
        msg = await self.recv()
        if msg != "config":
            raise RuntimeError(f"erwartet 'config', bekam {msg!r}")
        while True:
            msg = await self.recv()
            if msg == "ok":
                break
            # 'set key value' -> z.B. game.time_account merken
            parts = msg.split(" ", 2)
            if (
                parts[0] == "set"
                and len(parts) == 3
                and parts[1].endswith("time_account")
            ):
                try:
                    self.time_remaining = float(parts[2])
                except ValueError:
                    pass
        await self.send("ok")  # Config akzeptieren

    def _budget_for_move(self) -> float:
        """Dynamisches, phasen- und restzeit-abhaengiges Zeitbudget pro Zug.

        Drei Faktoren wirken zusammen:
          1. Neutrales Budget = min(base, Restkonto/20). Skaliert mit der
             Restzeit -> je weniger uebrig, desto kuerzer denken wir; wir
             verlieren nie auf Zeit (Konto reicht immer fuer >=20 weitere Zuege).
          2. Spielphasen-Faktor (_PHASE_BUDGET): Eroeffnung kurz, Mittelspiel
             lang, Endspiel solide.
          3. Harte Deckel: nie <0.2 s, nie >1/6 des Restkontos und nie >3x base,
             damit ein einzelner Zug das Konto nicht sprengt.
        `--time` (base) ist damit kein starres 5-s-Limit mehr, sondern der
        Anker, um den herum dynamisch skaliert wird.
        """
        base = self.per_move_time_s
        if self.time_remaining is None:
            return base
        factor = _PHASE_BUDGET.get(game_phase(self.board), 1.0)
        neutral = min(base, self.time_remaining / 20.0)
        hard_cap = min(self.time_remaining / 6.0, base * 3.0)
        return max(0.2, min(neutral * factor, hard_cap))

    def _record_position(self, board) -> None:
        self.seen[board] = self.seen.get(board, 0) + 1

    def _our_advantage(self, board) -> float:
        """evaluate() aus Sicht der eigenen Seite: positiv = wir stehen besser."""
        from src.evaluation import evaluate

        score = evaluate(board)
        return score if self.our_side == WHITE else -score

    def _repetition_alternative(self, min_advantage: float):
        """Bester nicht-wiederholender Zug, dessen Stellung uns nicht unter
        `min_advantage` bringt. Gibt (move, advantage) oder None zurueck."""
        maximize = self.our_side == WHITE
        best_move: Optional[Move] = None
        best_adv: Optional[float] = None
        best_score: Optional[float] = None
        from src.evaluation import evaluate

        for mv in generate_legal_moves(self.board, self.board.side_to_move):
            nb = apply_move_server_faithful(self.board, mv)
            if self.seen.get(nb, 0) >= 2:
                continue  # wuerde Dreifachwiederholung erzeugen
            score = evaluate(nb)
            if best_score is None or (
                score > best_score if maximize else score < best_score
            ):
                best_move, best_score = mv, score
                best_adv = score if self.our_side == WHITE else -score
        if best_move is None or best_adv is None or best_adv < min_advantage:
            return None
        return best_move

    def _choose_and_apply_our_move(self) -> Optional[Move]:
        if self.board.side_to_move != self.our_side:
            log.warning(
                "Zugrecht stimmt nicht: Brett=%s, wir=%s",
                self.board.side_to_move,
                self.our_side,
            )
        self.ai.time_limit_s = self._budget_for_move()
        move = self.ai.choose_move(self.board)
        if move is None:
            return None

        candidate = apply_move_server_faithful(self.board, move)
        # Wiederholungs-Vermeidung -- aber NUR wenn wir gewinnen:
        #   * stehen wir besser -> Remis waere Verschenken, also Loop brechen,
        #     solange die Alternative uns nicht selbst unter ~ausgeglichen bringt.
        #   * stehen wir gleich/schlechter -> Wiederholung ANNEHMEN (Remis ist
        #     besser als ein erzwungener Verlustzug). Genau der Fall, der uns in
        #     contest6 sonst ein Remis in eine Niederlage verwandelt haette.
        if self.seen.get(candidate, 0) >= 2:
            advantage = self._our_advantage(candidate)
            if advantage > 0:  # wir stehen besser -> Loop lohnt sich zu brechen
                alt = self._repetition_alternative(min_advantage=0.0)
                if alt is not None and alt != move:
                    log.info(
                        "Wiederholung vermieden (Vorteil %.1f): %s statt %s",
                        advantage,
                        alt,
                        move,
                    )
                    move = alt
                    candidate = apply_move_server_faithful(self.board, move)
            else:
                log.info(
                    "Wiederholung angenommen (Vorteil %.1f) -> Remis statt Risiko",
                    advantage,
                )

        # Authoritatives Brett mit Server-treuen Schlagregeln pflegen (Sync!).
        self.board = candidate
        self._record_position(self.board)
        return move

    def _apply_opponent_move(self, arg: str) -> None:
        move = move_from_server(arg)
        legal = generate_legal_moves(self.board, self.board.side_to_move)
        if move not in legal:
            log.warning("Gegnerzug %s nicht in unseren legalen Zuegen!", move)
        self.board = apply_move_server_faithful(self.board, move)
        self._record_position(self.board)

    async def _play(self) -> None:
        # Erste Nachricht entscheidet ueber unsere Seite.
        first = await self.recv(timeout=None)
        if first == "start":
            self.our_side = BLACK  # Spieler 0 zieht zuerst
            log.info("Wir sind SCHWARZ (Spieler 0) und ziehen zuerst.")
            move = self._choose_and_apply_our_move()
            if move is not None:
                await self.send(f"move {move_to_server(move)}")
        elif first == "wait":
            self.our_side = WHITE  # Spieler 1
            log.info("Wir sind WEISS (Spieler 1) und warten auf den ersten Zug.")
        else:
            raise RuntimeError(f"erwartet 'start'/'wait', bekam {first!r}")

        # Hauptschleife bis 'over'.
        while True:
            msg = await self.recv(timeout=None)
            cmd, _, rest = msg.partition(" ")

            if cmd == "over":
                log.info("=== Spiel beendet (over) ===")
                break
            if cmd == "time":
                try:
                    self.time_remaining = float(rest)
                except ValueError:
                    pass
                continue
            if cmd == "move":
                self._apply_opponent_move(rest)
                our = self._choose_and_apply_our_move()
                if our is None:
                    log.info("Kein legaler Zug mehr -- warte auf 'over'.")
                    continue
                await self.send(f"move {move_to_server(our)}")
                continue
            if cmd == "err":
                log.warning("Server-Fehler: %s", rest)
                continue
            # 'set', 'queued', 'lobby' etc. ignorieren

    async def play_host(
        self, lobby: str, start_pos: str = "", time_account: float = 300.0
    ) -> None:
        await self.connect_as_host(
            lobby, start_pos=start_pos, time_account=time_account
        )
        await self._await_queued_as_host()
        await self._config_phase()
        await self._play()
        await self.close()

    async def play_join(self, lobby: str) -> None:
        await self.connect_and_join(lobby)
        await self._await_queued_as_joiner()
        await self._config_phase()
        await self._play()
        await self.close()

    async def close(self) -> None:
        if self.writer is not None:
            try:
                await self.send("disconnect")
            except Exception:
                pass
            self.writer.close()


def main() -> None:
    p = argparse.ArgumentParser(description="DeepKnight Gameserver-Client (Tablut)")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--lobby", required=True, help="Lobby-Name")
    p.add_argument(
        "--create",
        action="store_true",
        help="Lobby als Host erstellen + Tablut konfigurieren (sonst beitreten)",
    )
    p.add_argument(
        "--time", type=float, default=1.0, help="Basis-Zeitbudget pro Zug in Sekunden"
    )
    p.add_argument(
        "--time-account",
        type=float,
        default=300.0,
        help="Zeitkonto pro Spieler fuer die ganze Partie (nur Host)",
    )
    p.add_argument(
        "--start-pos", default="", help="optionale FEN-Startstellung (nur Host)"
    )
    p.add_argument("--username", default=None)
    args = p.parse_args()

    client = TablutServerClient(
        host=args.host,
        port=args.port,
        per_move_time_s=args.time,
        username=args.username,
    )
    if args.create:
        asyncio.run(
            client.play_host(
                args.lobby,
                start_pos=args.start_pos,
                time_account=args.time_account,
            )
        )
    else:
        asyncio.run(client.play_join(args.lobby))


if __name__ == "__main__":
    main()
