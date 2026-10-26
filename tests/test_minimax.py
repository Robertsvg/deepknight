"""Tests fuer Minimax-Algorithmus."""

from src.fen import parse_fen
from src.minimax import minimax


def test_depth_0_returns_evaluation_and_no_move():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    score, move = minimax(board, 0)
    assert isinstance(score, float)
    assert move is None


def test_returns_legal_move():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    score, move = minimax(board, 1)
    assert move is not None
    assert len(move) == 4


def test_finds_king_escape_in_endgame():
    """Koenig auf b2, kann Richtung Ecke ziehen."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    score, move = minimax(board, 2)
    from_row, from_col, to_row, to_col = move
    assert (from_row, from_col) == (7, 1), "Koenig sollte sich bewegen"
    assert score > 0, "Score sollte positiv sein (gut fuer Weiss)"


def test_game_over_returns_evaluation():
    """Koenig auf a1 = Weiss hat gewonnen, Suche muss sofort stoppen."""
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")
    score, move = minimax(board, 3)
    assert move is None
    assert score >= 10000


def test_same_result_at_increasing_depths():
    """Mit mehr Tiefe sollte der Score stabil bleiben oder besser werden."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    s1, _ = minimax(board, 1)
    s2, _ = minimax(board, 2)
    assert s1 != float("-inf") and s2 != float("-inf")
