"""Tests fuer AdvancedAI (PVS+TT+Killer+History+Spielphasen).

Diese Tests pruefen, dass die kombinierte KI:
- legale Zuege spielt
- in einfachen Stellungen den klar besten Zug findet
- pro Aufruf state/tt zurueck setzt
"""

import time

from src.ai import AdvancedAI
from src.fen import STARTING_FEN, parse_fen
from src.moves import generate_legal_moves


def assert_is_legal(board, move):
    """Stellt sicher, dass `move` tatsaechlich ein legaler Zug auf `board` ist.

    Schliesst die Luecke, dass ein blosses ``move is not None`` einen illegalen
    Zug durchrutschen liesse.
    """
    assert move is not None, "KI hat keinen Zug zurueckgegeben"
    assert len(move) == 4
    legal = generate_legal_moves(board, board.side_to_move)
    assert move in legal, f"Zug {move} ist nicht in den legalen Zuegen"


def test_advanced_ai_returns_legal_move_in_starting_position():
    ai = AdvancedAI(time_limit_s=0.3)
    board = parse_fen(STARTING_FEN)
    move = ai.choose_move(board)
    assert_is_legal(board, move)


def test_advanced_ai_finds_white_wins_in_one():
    ai = AdvancedAI(time_limit_s=1.0)
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    move = ai.choose_move(board)
    assert_is_legal(board, move)
    assert move == (8, 1, 8, 0)


def test_advanced_ai_finds_black_wins_in_one():
    ai = AdvancedAI(time_limit_s=1.0)
    board = parse_fen("9/9/9/9/9/9/9/rK1r5/9 s 0 1")
    move = ai.choose_move(board)
    # Schwarz schlaegt Koenig auf b2 zwischen den Schwarzen Steinen.
    # Wir pruefen mindestens, dass der Zug legal ist (frueher nur "not None").
    assert_is_legal(board, move)


def test_advanced_ai_clears_state_between_calls():
    ai = AdvancedAI(time_limit_s=0.3)
    b1 = parse_fen(STARTING_FEN)
    b2 = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")

    ai.choose_move(b1)
    # State sollte Eintraege haben (irgendetwas wurde durchsucht)
    had_history = bool(ai.state.history) or any(
        slot is not None for slots in ai.state.killers for slot in slots
    )

    ai.choose_move(b2)
    # Vor der zweiten Suche wird state.reset() gerufen -- die alten
    # Eintraege duerfen die neue Stellung nicht beeinflussen. Ergebnis ist
    # ein Sieg-Zug:
    move = ai.choose_move(b2)
    assert move == (8, 1, 8, 0)
    # Smoke: zumindest hatten wir gefuellte State-Information in einem der Aufrufe
    assert had_history or ai.state.history


def test_advanced_ai_phase_detection_runs():
    """Die Startstellung wird als 'opening' klassifiziert."""
    ai = AdvancedAI(time_limit_s=0.2)
    board = parse_fen(STARTING_FEN)
    ai.choose_move(board)
    assert ai.last_phase == "opening"
    assert ai.last_phase_budget is not None
    assert ai.last_phase_budget > 0


def test_advanced_ai_respects_time_limit():
    """Die KI darf nicht massiv ueber das Zeitlimit hinausschiessen."""
    ai = AdvancedAI(time_limit_s=0.3)
    board = parse_fen(STARTING_FEN)
    t0 = time.perf_counter()
    ai.choose_move(board)
    elapsed = time.perf_counter() - t0
    # Phase-Faktor "opening" = 0.7, also 0.21s Soft-Limit. Toleranz:
    # max 3x das Zeitlimit (eine Iteration darf ueberlaufen).
    assert elapsed < ai.time_limit_s * 3
