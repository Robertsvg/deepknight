"""Endspiel-Demo: KI findet Sieg-Zug in einer 'Gewinn in 1' Stellung.

Zeigt sauber dass die KI funktioniert - sie findet den korrekten besten Zug
und erkennt den Sieg.
"""

import time

from src.ai import AlphaBetaAI
from src.fen import parse_fen
from src.move_ordering import move_to_string
from src.moves import apply_move
from src.rules import is_game_over


def show_board(board):
    print(board)
    print()


def demo_endspiel():
    print()
    print("=" * 78)
    print("  ENDSPIEL-DEMO: KI löst 'Weiß gewinnt in 1 Zug'")
    print("  DeepKnight - endgame demonstration")
    print("=" * 78)
    print()

    fen = "9/9/9/9/9/9/1r7/9/1K7 w 0 1"
    print(f"  Stellung (FEN: {fen}):")
    print()
    board = parse_fen(fen)
    show_board(board)

    print("  Weiß ist am Zug. König b1 — eine Ecke (a1) ist nur 1 Feld entfernt.")
    print()
    print(
        "  KI denkt nach (Alpha-Beta mit 1 Sek Zeitlimit + iterativer Tiefensuche)..."
    )
    print()

    ai = AlphaBetaAI(time_limit_s=1.0)
    t0 = time.perf_counter()
    move = ai.choose_move(board)
    elapsed = time.perf_counter() - t0

    print("  KI-Entscheidung:")
    print(f"    Bester Zug:      {move} = {move_to_string(move)}")
    print(f"    Erreichte Tiefe: {ai.last_result.depth}")
    print(f"    Score:           {ai.last_result.score}")
    print(f"    Rechenzeit:      {elapsed:.2f} s")
    print()

    new_board = apply_move(board, move)
    print("  Stellung NACH dem Zug:")
    show_board(new_board)

    result = is_game_over(new_board)
    print(f"  Spielstatus: {result}")

    if result == "white_wins":
        print("  ✓ Weiß hat gewonnen — König auf Eckfeld erreicht!")

    print()
    print("=" * 78)
    print()
    print("  ZWEITE DEMO: 'Schwarz gewinnt in 1 Zug' (Sandwich-Schlag)")
    print()

    fen2 = "9/9/9/9/9/9/9/rK1r5/9 s 0 1"
    print(f"  Stellung (FEN: {fen2}):")
    print()
    board2 = parse_fen(fen2)
    show_board(board2)

    print("  Schwarz ist am Zug. König b2 zwischen 2 Schwarzen.")
    print("  KI denkt nach...")
    print()

    ai2 = AlphaBetaAI(time_limit_s=1.0)
    t0 = time.perf_counter()
    move2 = ai2.choose_move(board2)
    elapsed2 = time.perf_counter() - t0

    print("  KI-Entscheidung:")
    print(f"    Bester Zug:      {move2} = {move_to_string(move2)}")
    print(f"    Erreichte Tiefe: {ai2.last_result.depth}")
    print(f"    Score:           {ai2.last_result.score}")
    print(f"    Rechenzeit:      {elapsed2:.2f} s")
    print()

    new_board2 = apply_move(board2, move2)
    print("  Stellung NACH dem Zug:")
    show_board(new_board2)

    result2 = is_game_over(new_board2)
    print(f"  Spielstatus: {result2}")

    if result2 == "black_wins":
        print("  ✓ Schwarz hat gewonnen — König geschlagen!")

    print()
    print("=" * 78)


if __name__ == "__main__":
    demo_endspiel()
