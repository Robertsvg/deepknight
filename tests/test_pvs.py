"""Tests for Principal Variation Search."""

from src.alpha_beta import alpha_beta, alpha_beta_with_count
from src.fen import STARTING_FEN, parse_fen
from src.moves import generate_legal_moves
from src.pvs import pvs, pvs_with_count

SIMPLE_ENDGAME = "9/9/9/9/9/9/3r5/1K7/9 w 0 1"


def test_depth_0_returns_evaluation_and_no_move():
    board = parse_fen(SIMPLE_ENDGAME)

    score, move = pvs(board, 0)

    assert isinstance(score, float)
    assert move is None


def test_returns_legal_move():
    board = parse_fen(SIMPLE_ENDGAME)

    score, move = pvs(board, 1)

    assert isinstance(score, float)
    assert move in generate_legal_moves(board, board.side_to_move)


def test_same_score_as_alpha_beta_simple_position():
    board = parse_fen(SIMPLE_ENDGAME)

    for depth in [1, 2, 3]:
        alpha_beta_score, _ = alpha_beta(board.copy(), depth)
        pvs_score, _ = pvs(board.copy(), depth)

        assert pvs_score == alpha_beta_score


def test_same_score_as_alpha_beta_start_position():
    board = parse_fen(STARTING_FEN)

    for depth in [1, 2]:
        alpha_beta_score, _ = alpha_beta(board.copy(), depth)
        pvs_score, _ = pvs(board.copy(), depth)

        assert pvs_score == alpha_beta_score


def test_game_over_returns_evaluation_and_no_move():
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")

    score, move = pvs(board, 3)

    assert score >= 10000
    assert move is None


def test_pvs_counts_visited_nodes():
    board = parse_fen(SIMPLE_ENDGAME)

    score, move, nodes = pvs_with_count(board, 2)

    assert isinstance(score, float)
    assert move is not None
    assert nodes > 1


def test_pvs_visits_no_more_nodes_than_alpha_beta_when_ordering_helps():
    """PVS mit Move-Ordering soll Alpha-Beta ohne Ordering nicht uebertreffen.

    Toleranz 10%: PVS gewinnt auf gut sortierten Stellungen klar (Startstellung
    typisch 5800 vs 15400 Knoten = Faktor 2.6x), kann aber in pathologischen
    Faellen durch Re-Search leicht draufzahlen.
    """
    board = parse_fen(STARTING_FEN)

    alpha_beta_score, _, alpha_beta_nodes = alpha_beta_with_count(board.copy(), 3)
    pvs_score, _, pvs_nodes = pvs_with_count(board.copy(), 3)

    assert pvs_score == alpha_beta_score
    assert pvs_nodes <= int(alpha_beta_nodes * 1.1), (
        f"AB={alpha_beta_nodes}, PVS={pvs_nodes}"
    )
