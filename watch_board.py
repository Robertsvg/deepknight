"""Live-Board-Viewer für die Contest-Partie.

Liest die Züge aus dem Gameserver-Client-Log und zeichnet das Tablut-Brett
in Echtzeit neu, sobald ein Zug dazukommt. Am Spielende wird angezeigt, ob
wir gewonnen, verloren oder unentschieden gespielt haben.

Start:  python3 watch_board.py [logdatei]
Default-Log: /tmp/contest_ki.log
"""

import re
import sys
import time

sys.path.insert(0, "/Users/batu/Developer/deepknight")
from src.board import (
    ATTACKER,
    BLACK,
    CORNERS,
    DEFENDER,
    EMPTY,
    KING,
    WHITE,
    Board,
    setup_initial_position,
)
from src.rules import is_king_captured
from src.server_rules import apply_move_server_faithful

LOG = sys.argv[1] if len(sys.argv) > 1 else "/tmp/contest_ki.log"

SYM = {EMPTY: " ·", ATTACKER: " ●", DEFENDER: " ○", KING: " ♚"}
MOVE_RE = re.compile(r"move (\d),(\d),(\d),(\d)")


def parse_moves(text):
    """Alle Züge in Reihenfolge: (richtung, move). '->' = wir, '<-' = Gegner."""
    moves = []
    for line in text.splitlines():
        m = MOVE_RE.search(line)
        if not m:
            continue
        s = line.strip()
        who = "WIR" if s.startswith("->") else "GEGNER" if s.startswith("<-") else "?"
        moves.append((who, tuple(int(x) for x in m.groups())))
    return moves


def winner_of(board):
    """Server-treue Sieg-Erkennung aus der Endstellung: BLACK / WHITE / None."""
    kp = board.find_king()
    if kp is None or is_king_captured(board):
        return BLACK
    if kp in CORNERS:
        return WHITE
    return None


def render(board, n_moves, last_who, last_move, side, finished):
    out = []
    out.append("\033[2J\033[H")  # Bildschirm leeren
    out.append("  ╔════════════════════════════════════╗")
    out.append("  ║   DeepKnight — Contest LIVE         ║")
    out.append("  ╚════════════════════════════════════╝")
    out.append("")
    out.append("      0  1  2  3  4  5  6  7  8")
    out.append("    ┌" + "─" * 27 + "┐")
    for r in range(9):
        cells = "".join(SYM[board.get(r, c)] for c in range(9))
        out.append(f"  {r} │{cells} │")
    out.append("    └" + "─" * 27 + "┘")
    out.append("")
    out.append("   ● = Angreifer (Schwarz)   ○ = Verteidiger (Weiß)   ♚ = König")
    out.append("")
    out.append(f"   Züge gespielt: {n_moves}")
    if last_move:
        pretty = f"{last_move[0]},{last_move[1]} → {last_move[2]},{last_move[3]}"
        out.append(f"   Letzter Zug:   {last_who}  ({pretty})")
    seite = "SCHWARZ ●" if side == BLACK else "WEISS ○" if side is not None else "…"
    out.append(f"   Wir spielen:   {seite}")

    if finished:
        out.append("")
        w = winner_of(board)
        if w is None:
            banner = "  UNENTSCHIEDEN  (Remis)  "
        elif side is not None and w == side:
            banner = "  ★★★  GEWONNEN!  ★★★  "
        elif side is not None:
            banner = "  ✗✗✗  VERLOREN  ✗✗✗  "
        else:
            sieger = "SCHWARZ" if w == BLACK else "WEISS"
            banner = f"  SPIEL BEENDET — Sieger: {sieger}  "
        out.append("   ╔" + "═" * len(banner) + "╗")
        out.append("   ║" + banner + "║")
        out.append("   ╚" + "═" * len(banner) + "╝")
    print("\n".join(out), flush=True)


def main():
    last_count = -1
    last_finished = None
    while True:
        try:
            with open(LOG) as f:
                text = f.read()
        except FileNotFoundError:
            print("Warte auf Log…", flush=True)
            time.sleep(1)
            continue

        moves = parse_moves(text)
        finished = "Spiel beendet" in text
        side = None
        if "SCHWARZ" in text:
            side = BLACK
        elif "WEISS" in text:
            side = WHITE

        if len(moves) != last_count or finished != last_finished:
            board = Board()
            setup_initial_position(board)
            last_who, last_move = None, None
            for who, mv in moves:
                board = apply_move_server_faithful(board, mv)
                last_who, last_move = who, mv
            render(board, len(moves), last_who, last_move, side, finished)
            last_count = len(moves)
            last_finished = finished

        time.sleep(1)


if __name__ == "__main__":
    main()
