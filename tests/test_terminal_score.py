"""Tests fuer tiefenabhaengigen Sieg-Score.

Schnelle Siege muessen hoeher bewertet werden als spaete -- sonst kann die
KI einen sofortigen Sieg gleichbewerten wie einen Sieg in 5 Halbzuegen und
ggfs. den langsameren waehlen.
"""

from src.alpha_beta import alpha_beta_with_count
from src.alpha_beta_tt import alpha_beta_tt_with_count
from src.evaluation import WIN_SCORE, terminal_score
from src.fen import parse_fen
from src.minimax import minimax_with_count
from src.pvs import pvs_with_count

# --- terminal_score() Grundverhalten ------------------------------------


def test_terminal_score_returns_none_for_non_terminal_position():
    board = parse_fen("9/9/9/9/4K4/9/9/9/9 w 0 1")
    assert terminal_score(board, plies_from_root=0) is None


def test_terminal_score_white_win_at_root_equals_win_score():
    """plies_from_root=0 -> voller WIN_SCORE."""
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")
    assert terminal_score(board, plies_from_root=0) == WIN_SCORE


def test_terminal_score_white_win_after_two_plies_is_lower():
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")
    score_immediate = terminal_score(board, plies_from_root=0)
    score_later = terminal_score(board, plies_from_root=2)
    assert score_later < score_immediate
    assert score_later == WIN_SCORE - 2


def test_terminal_score_black_win_after_two_plies_is_less_negative():
    """Schwarz-Sieg: bei spaeterer Tiefe weniger negativ (weniger schlecht)."""
    board = parse_fen("9/9/9/9/9/9/9/9/9 s 0 1")  # Koenig fehlt -> Schwarz-Sieg
    score_immediate = terminal_score(board, plies_from_root=0)
    score_later = terminal_score(board, plies_from_root=2)
    assert score_immediate == -WIN_SCORE
    assert score_later == -WIN_SCORE + 2
    assert score_later > score_immediate


# --- Verhalten in der Suche ---------------------------------------------


def test_alpha_beta_prefers_immediate_white_win():
    """Wenn Weiss in 1 Halbzug gewinnen kann, muss der Score > Sieg-in-mehr sein."""
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    score, move, _ = alpha_beta_with_count(board, depth=4)
    # Sieg im naechsten Halbzug -> Score = WIN_SCORE - 1
    assert score == WIN_SCORE - 1
    assert move == (8, 1, 8, 0)


def test_alpha_beta_tt_prefers_immediate_white_win():
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    score, move, _ = alpha_beta_tt_with_count(board, depth=4)
    assert score == WIN_SCORE - 1
    assert move == (8, 1, 8, 0)


def test_minimax_prefers_immediate_white_win():
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    score, move, _ = minimax_with_count(board, depth=3)
    assert score == WIN_SCORE - 1
    assert move == (8, 1, 8, 0)


def test_pvs_prefers_immediate_white_win():
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    score, move, _ = pvs_with_count(board, depth=4)
    assert score == WIN_SCORE - 1
    assert move == (8, 1, 8, 0)


def test_all_searches_agree_on_quick_black_win_score():
    """Schwarz gewinnt in 1: alle Algorithmen muessen -WIN_SCORE + 1 liefern."""
    board = parse_fen("9/9/9/9/9/9/9/rK1r5/9 s 0 1")

    s_mm, _, _ = minimax_with_count(board.copy(), 3)
    s_ab, _, _ = alpha_beta_with_count(board.copy(), 3)
    s_tt, _, _ = alpha_beta_tt_with_count(board.copy(), 3)
    s_pvs, _, _ = pvs_with_count(board.copy(), 3)

    assert s_mm == -WIN_SCORE + 1
    assert s_ab == s_mm
    assert s_tt == s_mm
    assert s_pvs == s_mm
