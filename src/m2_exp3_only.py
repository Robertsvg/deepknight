"""Long-budget search experiment with a 120-second limit."""

import time

from src.alpha_beta import alpha_beta_with_count
from src.fen import parse_fen
from src.minimax import minimax_with_count

POSITIONS = [
    {
        "name": "Startstellung",
        "fen": "3rrr3/4r4/4R4/r3R3r/rrRRKRRrr/r3R3r/4R4/4r4/3rrr3 s 0 1",
        "skip_minimax_deep": True,
    },
    {
        "name": "Weiss gewinnt in 1",
        "fen": "9/9/9/9/9/9/1r7/9/1K7 w 0 1",
        "skip_minimax_deep": False,
    },
    {
        "name": "Schwarz gewinnt in 1",
        "fen": "9/9/9/9/9/9/9/rK1r5/9 s 0 1",
        "skip_minimax_deep": False,
    },
]


def log(msg):
    print(msg, flush=True)


def search_iterative_max(
    board, search_fn, time_limit_s, max_depth=12, branching_estimate=8.0
):
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


def fmt(s):
    if s < 0.01:
        return f"{s * 1000:.1f}ms"
    if s < 1:
        return f"{s * 1000:.0f}ms"
    return f"{s:.2f}s"


def run():
    log("=" * 100)
    log("EXPERIMENT 3 - Maximum search depth with a 120-second limit")
    log("=" * 100)

    for pos in POSITIONS:
        log(f"\n### {pos['name']} ###")
        log(f"FEN: {pos['fen']}")
        board = parse_fen(pos["fen"])

        log("\n>>> Minimax (max 120s)")
        if pos["skip_minimax_deep"]:
            r = search_iterative_max(board, minimax_with_count, 120.0, max_depth=4)
        else:
            r = search_iterative_max(board, minimax_with_count, 120.0)
        log(
            f"  Minimax:    depth={r['depth']}, nodes={r['nodes']:>10}, move={r['move']}, depth_time={fmt(r['depth_time'])}, total={fmt(r['elapsed'])}"
        )

        log("\n>>> AlphaBeta (max 120s)")
        r = search_iterative_max(board, alpha_beta_with_count, 120.0)
        log(
            f"  AlphaBeta:  depth={r['depth']}, nodes={r['nodes']:>10}, move={r['move']}, depth_time={fmt(r['depth_time'])}, total={fmt(r['elapsed'])}"
        )
        log("")

    log("\n=== FERTIG ===")


if __name__ == "__main__":
    run()
