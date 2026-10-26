"""Tests fuer Alpha-Beta-Suche.

Wichtigster Test: Alpha-Beta liefert das GLEICHE Ergebnis wie Minimax,
nur schneller. Wenn das nicht stimmt, ist der Algorithmus kaputt.
"""

from src.alpha_beta import alpha_beta
from src.fen import STARTING_FEN, parse_fen
from src.minimax import minimax


def test_depth_0_returns_evaluation_and_no_move():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    score, move = alpha_beta(board, 0)
    assert isinstance(score, float)
    assert move is None


def test_returns_legal_move():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    score, move = alpha_beta(board, 1)
    assert move is not None
    assert len(move) == 4


def test_same_score_as_minimax_simple():
    """Endspiel: Score muss zwischen Minimax und Alpha-Beta uebereinstimmen."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    for depth in [1, 2, 3]:
        s_mm, _ = minimax(board.copy(), depth)
        s_ab, _ = alpha_beta(board.copy(), depth)
        assert s_mm == s_ab, f"Tiefe {depth}: Minimax={s_mm}, AlphaBeta={s_ab}"


def test_same_score_as_minimax_startposition():
    """Startstellung: muss bei kleiner Tiefe uebereinstimmen."""
    board = parse_fen(STARTING_FEN)
    for depth in [1, 2]:
        s_mm, _ = minimax(board.copy(), depth)
        s_ab, _ = alpha_beta(board.copy(), depth)
        assert s_mm == s_ab, f"Tiefe {depth}: Minimax={s_mm}, AlphaBeta={s_ab}"


def test_game_over_returns_evaluation():
    """Koenig auf a1 = Weiss gewinnt sofort."""
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")
    score, move = alpha_beta(board, 3)
    assert move is None
    assert score >= 10000
