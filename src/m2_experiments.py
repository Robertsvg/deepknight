"""M2 Experimente fuer TubCloud-Tabelle "Alpha-Beta-KI".

FIX: Experiment 1 traegt nur Tiefen ein, die VOLLSTAENDIG innerhalb des
Zeitlimits abgeschlossen wurden.
"""

import time

from src.alpha_beta import alpha_beta_with_count
from src.evaluation import evaluate
from src.fen import parse_fen
from src.minimax import minimax_with_count

POSITIONS = [
    {
        "name": "Startstellung",
        "fen": "3rrr3/4r4/4R4/r3R3r/rrRRKRRrr/r3R3r/4R4/4r4/3rrr3 s 0 1",
        "description": "Initial Tablut Position, Schwarz beginnt",
        "skip_minimax_deep": True,
    },
    {
        "name": "Weiss gewinnt in 1",
        "fen": "9/9/9/9/9/9/1r7/9/1K7 w 0 1",
        "description": "Koenig b1 kann a1 (Ecke) erreichen, Weiss gewinnt sofort",
        "skip_minimax_deep": False,
    },
    {
        "name": "Schwarz gewinnt in 1",
        "fen": "9/9/9/9/9/9/9/rK1r5/9 s 0 1",
        "description": "Koenig b2 zwischen 2 Schwarzen, Schwarz schlaegt sofort",
        "skip_minimax_deep": False,
    },
]


def log(msg):
    print(msg, flush=True)


def benchmark_evaluation(board, iterations=10000):
    t0 = time.perf_counter()
    for _ in range(iterations):
        evaluate(board)
    return time.perf_counter() - t0


def search_iterative(
    board, search_fn, time_limit_s, max_depth=12, branching_estimate=8.0
):
    """Iterative Tiefensuche mit korrektem Zeitlimit.

    Eine Tiefe wird NUR uebernommen, wenn sie VOLLSTAENDIG innerhalb des
    Zeitlimits abgeschlossen wurde.

    Wir schaetzen vor jeder Tiefe: wird die voraussichtlich noch innerhalb
    des Limits fertig? Annahme: naechste Tiefe braucht 'branching_estimate'-
    mal so lange wie die vorherige. Wenn nicht passend, brechen wir ab.
    """
    depth = 1
    best = {"depth": 0, "nodes": 0, "move": None, "score": None, "depth_time": 0.0}
    t_start = time.perf_counter()
    last_depth_time = 0.0

    while depth <= max_depth:
        elapsed = time.perf_counter() - t_start
        remaining = time_limit_s - elapsed
        if remaining <= 0:
            break

        if last_depth_time > 0 and last_depth_time * branching_estimate > remaining:
            break

        counter = [0]
        try:
            t_d = time.perf_counter()
            score, move, _ = search_fn(board.copy(), depth, counter=counter)
            d_end = time.perf_counter()

            time_total = d_end - t_start
            time_for_depth = d_end - t_d

            if time_total <= time_limit_s:
                best = {
                    "depth": depth,
                    "nodes": counter[0],
                    "move": move,
                    "score": score,
                    "depth_time": time_for_depth,
                }
                last_depth_time = time_for_depth
            else:
                break

        except Exception:
            break

        depth += 1

    best["elapsed"] = time.perf_counter() - t_start
    return best


def search_fixed_depth(board, search_fn, depth, hard_limit_s):
    """Suche mit festem Tiefenlimit. Bricht ab wenn Zeit das harte Limit ueberschreitet."""
    counter = [0]
    t0 = time.perf_counter()
    try:
        score, move, _ = search_fn(board.copy(), depth, counter=counter)
        elapsed = time.perf_counter() - t0
        if elapsed > hard_limit_s:
            return {"timed_out": True, "elapsed": elapsed, "nodes": counter[0]}
        return {
            "depth": depth,
            "nodes": counter[0],
            "move": move,
            "score": score,
            "elapsed": elapsed,
        }
    except Exception as e:
        return {
            "error": str(e),
            "elapsed": time.perf_counter() - t0,
            "nodes": counter[0],
        }


def fmt(s):
    if s < 0.001:
        return f"{s * 1000:.2f}ms"
    if s < 0.01:
        return f"{s * 1000:.1f}ms"
    if s < 1:
        return f"{s * 1000:.0f}ms"
    return f"{s:.2f}s"


def run_position(pos, t1=1.0, d2=4, t3=20.0):
    log(f"\n{'=' * 100}")
    log(f"### {pos['name']} ###")
    log(f"FEN: {pos['fen']}")
    log(f"{pos['description']}")
    log("=" * 100)

    board = parse_fen(pos["fen"])

    eval_time = benchmark_evaluation(board, 10000)
    log(f"\n>>> Bewertungsfunktion 10000x: {fmt(eval_time)}")

    log(
        f"\n>>> Experiment 1: {t1}s Zeitlimit (Iterative Deepening, NUR vollstaendig durchsuchte Tiefen)"
    )

    log("  Minimax startet...")
    max_d_minimax = 2 if pos["skip_minimax_deep"] else 12
    r = search_iterative(board, minimax_with_count, t1, max_depth=max_d_minimax)
    log(
        f"  Minimax:    depth={r['depth']}, nodes={r['nodes']:>10}, move={r['move']}, score={r['score']}, depth_time={fmt(r['depth_time'])}, total={fmt(r['elapsed'])}"
    )

    log("  AlphaBeta startet...")
    r = search_iterative(board, alpha_beta_with_count, t1)
    log(
        f"  AlphaBeta:  depth={r['depth']}, nodes={r['nodes']:>10}, move={r['move']}, score={r['score']}, depth_time={fmt(r['depth_time'])}, total={fmt(r['elapsed'])}"
    )

    log(f"\n>>> Experiment 2: Festes Tiefenlimit {d2}")

    if pos["skip_minimax_deep"]:
        actual_d = d2 - 1
        log(
            f"  Minimax bei Tiefe {d2} dauert zu lange - skip (Tiefe {actual_d} stattdessen)"
        )
        r = search_fixed_depth(board, minimax_with_count, actual_d, t3)
        if r.get("timed_out"):
            log(
                f"  Minimax (T{actual_d}):  TIMEOUT ({fmt(r['elapsed'])}), nodes={r['nodes']}"
            )
        else:
            log(
                f"  Minimax (T{actual_d}):  time={fmt(r['elapsed'])}, nodes={r['nodes']:>10}, move={r['move']}"
            )
    else:
        log("  Minimax startet...")
        r = search_fixed_depth(board, minimax_with_count, d2, t3)
        if r.get("timed_out"):
            log(f"  Minimax:    TIMEOUT ({fmt(r['elapsed'])}), nodes={r['nodes']}")
        else:
            log(
                f"  Minimax:    time={fmt(r['elapsed'])}, nodes={r['nodes']:>10}, move={r['move']}"
            )

    log("  AlphaBeta startet...")
    r = search_fixed_depth(board, alpha_beta_with_count, d2, t3)
    if r.get("timed_out"):
        log(f"  AlphaBeta:  TIMEOUT ({fmt(r['elapsed'])}), nodes={r['nodes']}")
    else:
        log(
            f"  AlphaBeta:  time={fmt(r['elapsed'])}, nodes={r['nodes']:>10}, move={r['move']}"
        )

    log(f"\n>>> Experiment 3: Maximum ausreizen (max {t3:.0f}s pro Algorithmus)")

    log(f"  Minimax startet (max {t3:.0f}s)...")
    if pos["skip_minimax_deep"]:
        r = search_iterative(board, minimax_with_count, t3, max_depth=3)
    else:
        r = search_iterative(board, minimax_with_count, t3)
    log(
        f"  Minimax:    depth={r['depth']}, nodes={r['nodes']:>10}, move={r['move']}, score={r['score']}, depth_time={fmt(r['depth_time'])}, total={fmt(r['elapsed'])}"
    )

    log(f"  AlphaBeta startet (max {t3:.0f}s)...")
    r = search_iterative(board, alpha_beta_with_count, t3)
    log(
        f"  AlphaBeta:  depth={r['depth']}, nodes={r['nodes']:>10}, move={r['move']}, score={r['score']}, depth_time={fmt(r['depth_time'])}, total={fmt(r['elapsed'])}"
    )


def run_all():
    log("=" * 100)
    log("BASELINE SEARCH EXPERIMENTS - DeepKnight")
    log("=" * 100)

    for pos in POSITIONS:
        run_position(pos, t1=1.0, d2=4, t3=20.0)

    log("\n\n=== ALLE EXPERIMENTE FERTIG ===")


if __name__ == "__main__":
    run_all()
