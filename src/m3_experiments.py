"""M3-Benchmarks fuer TubCloud-Tabelle "Erweiterte KI".

Vergleicht die 7 Konfigurationen aus docs/MST3.md auf den gleichen Stellungen:
  1) Alpha-Beta (M2-Baseline)
  2) Alpha-Beta + Transposition Table
  3) Alpha-Beta + erweiterte Zugsortierung (Killer + History) ohne TT
  4) PVS
  5) PVS + Transposition Table
  6) PVS + TT + erweiterte Zugsortierung (Killer + History)
  7) AdvancedAI (= PVS + TT + Killer + History + Spielphasen-Zeitmanagement)

Stellungen:
  - Startstellung (Schwarz am Zug)
  - "Weiss gewinnt in 1"
  - "Schwarz gewinnt in 1"
  - "Weiss gewinnt in 2" (two-ply tactical position)
  - Mid-Game-Sample
  - Endspiel

Pro Konfig + Stellung messen wir:
  - tiefste vollstaendig durchsuchte Tiefe in 1 Sekunde
  - untersuchte Knoten bei dieser Tiefe
  - gewaehlter Zug + Score
"""

import sys
import time

from src.alpha_beta import alpha_beta_with_count
from src.alpha_beta_tt import alpha_beta_tt_with_count
from src.evaluation import WIN_SCORE, evaluate, game_phase
from src.fen import parse_fen
from src.pvs import pvs_with_count
from src.search_state import SearchState
from src.time_manager import PHASE_FACTORS
from src.transposition_table import (
    TranspositionTable,
)

# Fixed positions for repeatable search comparisons.
POSITIONS = [
    {
        "name": "Startstellung",
        "fen": "3rrr3/4r4/4R4/r3R3r/rrRRKRRrr/r3R3r/4R4/4r4/3rrr3 s 0 1",
        "max_minimax_depth": 2,
    },
    {
        "name": "Weiss gewinnt in 1",
        "fen": "9/9/9/9/9/9/1r7/9/1K7 w 0 1",
        "max_minimax_depth": 6,
    },
    {
        "name": "Schwarz gewinnt in 1",
        "fen": "9/9/9/9/9/9/9/rK1r5/9 s 0 1",
        "max_minimax_depth": 6,
    },
    {
        "name": "Weiss gewinnt in 2",
        # K auf b3, ein Angreifer auf c4. Weiss zieht K b3->a3, dann a3->a1 (Ecke).
        # Schwarz hat eigene Zuege (kein Pattszenario wie eine zu leere Stellung).
        "fen": "9/9/9/9/9/2r6/1K7/9/9 w 0 1",
        "max_minimax_depth": 6,
    },
    {
        "name": "Mid-Game-Sample",
        "fen": "3rrr3/4r4/4R4/r3R3r/rr1RKR1rr/r3R3r/4R4/4r4/3rrr3 w 0 1",
        "max_minimax_depth": 3,
    },
    {
        "name": "Endspiel",
        "fen": "9/9/9/9/9/9/3r5/1K7/9 w 0 1",
        "max_minimax_depth": 5,
    },
]


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt(s: float) -> str:
    if s < 0.001:
        return f"{s * 1000:.2f}ms"
    if s < 0.01:
        return f"{s * 1000:.1f}ms"
    if s < 1:
        return f"{s * 1000:.0f}ms"
    return f"{s:.2f}s"


def iter_search(
    board, search_callable, time_limit_s, max_depth=12, branching_estimate=8.0
):
    """Iterative Deepening mit korrektem Zeitlimit.

    `search_callable(board, depth)` -> (score, move, nodes)
    Nur Tiefen, die VOLLSTAENDIG innerhalb des Zeitlimits beendet wurden,
    werden uebernommen.
    """
    best = {
        "depth": 0,
        "nodes": 0,
        "move": None,
        "score": None,
        "depth_time": 0.0,
    }
    t_start = time.perf_counter()
    last_depth_time = 0.0

    for depth in range(1, max_depth + 1):
        elapsed = time.perf_counter() - t_start
        remaining = time_limit_s - elapsed
        if remaining <= 0:
            break
        if last_depth_time > 0 and last_depth_time * branching_estimate > remaining:
            break

        try:
            t_d = time.perf_counter()
            score, move, nodes = search_callable(board.copy(), depth)
            d_end = time.perf_counter()
        except Exception as exc:
            log(f"    [Tiefe {depth}] Fehler: {exc}")
            break

        time_total = d_end - t_start
        depth_time = d_end - t_d

        if time_total <= time_limit_s:
            best = {
                "depth": depth,
                "nodes": nodes,
                "move": move,
                "score": score,
                "depth_time": depth_time,
            }
            last_depth_time = depth_time
        else:
            break

    best["elapsed"] = time.perf_counter() - t_start
    return best


# --- Konfigurationen ---------------------------------------------------------


def run_alpha_beta(board, depth):
    counter = [0]
    score, move, _ = alpha_beta_with_count(board, depth, counter=counter)
    return score, move, counter[0]


def make_alpha_beta_tt():
    tt = TranspositionTable()

    def fn(board, depth):
        counter = [0]
        score, move, _ = alpha_beta_tt_with_count(
            board, depth, -WIN_SCORE, WIN_SCORE, tt, counter, 0, None
        )
        return score, move, counter[0]

    return fn


def make_alpha_beta_ordering():
    """AB + Killer + History OHNE TT. Inline-Variante mit SearchState,
    aber tt=None in alpha_beta_tt_with_count -- das gibt genau diese Konfig."""
    state = SearchState()

    def fn(board, depth):
        counter = [0]
        # alpha_beta_tt_with_count mit tt=None legt intern eine frische TT an,
        # die nicht persistiert -- also effektiv "kein TT-Reuse". Killer/History
        # bleiben aber durch state erhalten.
        # Fuer "wirklich ohne TT" simulieren wir das: pro Aufruf neue TT.
        tt = TranspositionTable()
        score, move, _ = alpha_beta_tt_with_count(
            board, depth, -WIN_SCORE, WIN_SCORE, tt, counter, 0, state
        )
        return score, move, counter[0]

    return fn


def run_pvs(board, depth):
    counter = [0]
    score, move, _ = pvs_with_count(board, depth, counter=counter)
    return score, move, counter[0]


def make_pvs_tt():
    tt = TranspositionTable()

    def fn(board, depth):
        counter = [0]
        score, move, _ = pvs_with_count(
            board, depth, -WIN_SCORE, WIN_SCORE, counter, 0, tt, None
        )
        return score, move, counter[0]

    return fn


def make_pvs_tt_state():
    tt = TranspositionTable()
    state = SearchState()

    def fn(board, depth):
        counter = [0]
        score, move, _ = pvs_with_count(
            board, depth, -WIN_SCORE, WIN_SCORE, counter, 0, tt, state
        )
        return score, move, counter[0]

    return fn


def make_advanced_ai(initial_board):
    """Konfig 7: AdvancedAI mit Spielphasen-Zeitmanagement.

    Wir bestimmen die Spielphase einmal aus der Wurzelstellung (so wie
    AdvancedAI.choose_move es macht). Das Time-Budget wird im iter_search-
    Aufrufer skaliert.
    """
    tt = TranspositionTable()
    state = SearchState()

    def fn(board, depth):
        counter = [0]
        score, move, _ = pvs_with_count(
            board, depth, -WIN_SCORE, WIN_SCORE, counter, 0, tt, state
        )
        return score, move, counter[0]

    return fn


def run_position(pos, time_limit_s=1.0):
    log(f"\n{'=' * 100}")
    log(f"### {pos['name']} ###")
    log(f"FEN: {pos['fen']}")
    log("=" * 100)

    board = parse_fen(pos["fen"])

    # Bewertungsfunktion-Geschwindigkeit
    t0 = time.perf_counter()
    for _ in range(10000):
        evaluate(board)
    eval_time = time.perf_counter() - t0
    log(f"  evaluate() x10000: {fmt(eval_time)}  ({10000 / eval_time:.0f} /s)")

    phase = game_phase(board)
    log(
        f"  Spielphase laut game_phase(): {phase}  (Zeitfaktor={PHASE_FACTORS.get(phase, 1.0)})"
    )
    log("")
    log(
        "  Konfiguration                                     Tiefe   Knoten  Score   bester Zug"
    )
    log(f"  {'-' * 96}")

    configs = [
        ("[1] Alpha-Beta (M2-Baseline)", run_alpha_beta, time_limit_s),
        ("[2] AB + TT", make_alpha_beta_tt(), time_limit_s),
        (
            "[3] AB + ext. Zugsortierung (Killer+History)",
            make_alpha_beta_ordering(),
            time_limit_s,
        ),
        ("[4] PVS", run_pvs, time_limit_s),
        ("[5] PVS + TT", make_pvs_tt(), time_limit_s),
        ("[6] PVS + TT + Killer + History", make_pvs_tt_state(), time_limit_s),
        # Konfig 7: AdvancedAI -- nutzt zusaetzlich Spielphasen-Zeitmanagement
        (
            "[7] AdvancedAI (PVS+TT+K+H+Phasen)",
            make_advanced_ai(board),
            time_limit_s * PHASE_FACTORS.get(phase, 1.0),
        ),
    ]

    for label, search_callable, t_lim in configs:
        r = iter_search(board, search_callable, t_lim, max_depth=12)
        log(
            f"  {label:<50} {r['depth']:>5}   {r['nodes']:>7d}   "
            f"{(r['score'] if r['score'] is not None else 0):>6.0f}  {r['move']}"
        )


def run_all(time_limit_s=1.0):
    log("=" * 100)
    log(
        f"SEARCH EXPERIMENTS - DeepKnight (time limit: {time_limit_s}s per configuration)"
    )
    log("=" * 100)

    for pos in POSITIONS:
        run_position(pos, time_limit_s=time_limit_s)

    log("\n\n=== ALLE EXPERIMENTE FERTIG ===\n")


if __name__ == "__main__":
    t_limit = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    run_all(time_limit_s=t_limit)
