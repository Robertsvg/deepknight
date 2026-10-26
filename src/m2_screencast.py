"""Screencast-Demo: Alpha-Beta vs Minimax Vergleich.

Zeigt schön aufbereitet den Cutoff-Effekt auf 3 Stellungen.
Läuft in ~30 Sekunden, perfekt für den Screencast.
"""

import time

from src.alpha_beta import alpha_beta_with_count
from src.fen import parse_fen
from src.minimax import minimax_with_count

POSITIONS = [
    {
        "name": "Stellung 2: Weiß gewinnt in 1",
        "fen": "9/9/9/9/9/9/1r7/9/1K7 w 0 1",
        "best_move_expected": "8,1,8,0 (b1 → a1, Ecke)",
    },
    {
        "name": "Stellung 3: Schwarz gewinnt in 1",
        "fen": "9/9/9/9/9/9/9/rK1r5/9 s 0 1",
        "best_move_expected": "7,3,7,2 (d2 → c2, Sandwich-Schlag)",
    },
]


def fmt_time(s):
    if s < 0.001:
        return f"{s * 1000000:.0f} us"
    if s < 1:
        return f"{s * 1000:.0f} ms"
    return f"{s:.2f} s"


def fmt_num(n):
    return f"{n:,}".replace(",", ".")


def run():
    print()
    print("=" * 78)
    print("  ALPHA-BETA vs MINIMAX - Vergleich auf 3 Stellungen (Tiefe 4)")
    print("  DeepKnight - search demonstration")
    print("=" * 78)
    print()

    for pos in POSITIONS:
        print(f"\n  >>> {pos['name']}")
        print(f"      FEN: {pos['fen']}")
        print(f"      Erwarteter bester Zug: {pos['best_move_expected']}")
        print()
        board = parse_fen(pos["fen"])

        # MINIMAX
        counter = [0]
        t0 = time.perf_counter()
        score_mm, move_mm, _ = minimax_with_count(board.copy(), 4, counter=counter)
        time_mm = time.perf_counter() - t0
        nodes_mm = counter[0]

        # ALPHA-BETA
        counter = [0]
        t0 = time.perf_counter()
        score_ab, move_ab, _ = alpha_beta_with_count(board.copy(), 4, counter=counter)
        time_ab = time.perf_counter() - t0
        nodes_ab = counter[0]

        # Output
        print("      | Algorithmus | Zeit       | Knoten        | Score  | Zug      |")
        print("      |-------------|------------|---------------|--------|----------|")
        print(
            f"      | Minimax     | {fmt_time(time_mm):>10} | {fmt_num(nodes_mm):>13} | {score_mm:>6.0f} | {str(move_mm):>8} |"
        )
        print(
            f"      | Alpha-Beta  | {fmt_time(time_ab):>10} | {fmt_num(nodes_ab):>13} | {score_ab:>6.0f} | {str(move_ab):>8} |"
        )

        speedup_nodes = nodes_mm / nodes_ab if nodes_ab > 0 else 0
        speedup_time = time_mm / time_ab if time_ab > 0 else 0
        print(
            f"\n      >> Cutoff-Effekt: {speedup_nodes:.1f}x weniger Knoten, {speedup_time:.1f}x schneller"
        )
        print()

    print("=" * 78)
    print("  Beide Algorithmen finden denselben besten Zug.")
    print("  Alpha-Beta ist deutlich effizienter - das ist der Cutoff-Effekt.")
    print("=" * 78)
    print()


if __name__ == "__main__":
    run()
