import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation import (
    ATTACKER_VALUE,
    DEFENDER_VALUE,
    ESCAPE_LANE_WEIGHT,
    KING_DISTANCE_WEIGHT,
    KING_MOBILITY_WEIGHT,
    WIN_SCORE,
    corner_approach_score,
    defender_shield_score,
    escape_lane_score,
    evaluate,
    game_phase,
    king_danger_score,
    king_distance_score,
    king_mobility_score,
    material_score,
)
from src.fen import STARTING_FEN, parse_fen


def test_white_win_scores_high():
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")

    assert evaluate(board) == WIN_SCORE


def test_black_win_scores_low_when_king_missing():
    board = parse_fen("9/9/9/9/9/9/9/9/9 s 0 1")

    assert evaluate(board) == -WIN_SCORE


def test_draw_scores_zero():
    board = parse_fen("9/9/9/9/4K4/9/9/9/9 w 50 10")

    assert evaluate(board) == 0.0


def test_material_counts_defenders_minus_attackers():
    board = parse_fen("9/9/9/9/2R1K1r2/9/9/9/9 w 0 1")

    assert material_score(board) == DEFENDER_VALUE - ATTACKER_VALUE


def test_king_closer_to_corner_is_better():
    center = parse_fen("9/9/9/9/4K4/9/9/9/9 w 0 1")
    near_corner = parse_fen("9/9/9/9/9/9/9/1K7/9 w 0 1")

    assert king_distance_score(near_corner) > king_distance_score(center)


def test_non_terminal_evaluation_combines_all_components():
    board = parse_fen("9/9/9/9/2R1K1r2/9/9/9/9 w 0 1")
    expected = (
        material_score(board)
        + king_distance_score(board)
        + king_mobility_score(board)
        + escape_lane_score(board)
        + king_danger_score(board)
        + corner_approach_score(board)
        + defender_shield_score(board)
    )

    assert evaluate(board) == expected


def test_king_distance_uses_configured_weight():
    # King at (7, 1). Nearest corner is (8, 0), Manhattan distance = 2.
    # closeness = MAX_KING_CORNER_DISTANCE(16) - 2 = 14
    board = parse_fen("9/9/9/9/9/9/9/1K7/9 w 0 1")

    assert king_distance_score(board) == 14 * KING_DISTANCE_WEIGHT


def test_game_phase_detects_opening_from_start_position():
    board = parse_fen(STARTING_FEN)

    assert game_phase(board) == "opening"


def test_game_phase_detects_midgame_after_king_leaves_center():
    board = parse_fen("3rrr3/4r4/4R4/r3R3r/rrRR1KRrr/r3R3r/4R4/4r4/3rrr3 w 0 1")

    assert game_phase(board) == "midgame"


def test_game_phase_detects_endgame_when_king_is_near_corner():
    board = parse_fen("9/K8/9/9/9/9/9/9/9 w 0 1")

    assert game_phase(board) == "endgame"


def test_king_mobility_score_uses_configured_weight():
    board = parse_fen("9/9/9/9/4K4/9/9/9/9 w 0 1")

    assert king_mobility_score(board) == 16 * KING_MOBILITY_WEIGHT


def test_escape_lane_rewards_clear_corner_path():
    board = parse_fen("9/K8/9/9/9/9/9/9/9 w 0 1")
    blocked = parse_fen("r8/K8/9/9/9/9/9/9/9 w 0 1")

    assert escape_lane_score(board) == 2 * ESCAPE_LANE_WEIGHT
    assert escape_lane_score(blocked) == ESCAPE_LANE_WEIGHT


def test_king_danger_penalizes_nearby_attackers():
    safe = parse_fen("9/9/9/9/4K4/9/9/9/9 w 0 1")
    threatened = parse_fen("9/9/9/4r4/4K4/4r4/9/9/9 w 0 1")

    assert king_danger_score(threatened) < king_danger_score(safe)
