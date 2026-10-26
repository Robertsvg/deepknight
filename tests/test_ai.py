from src.ai import PVSAI
from src.evaluation import game_phase
from src.fen import STARTING_FEN, parse_fen
from src.moves import generate_legal_moves
from src.time_manager import PHASE_FACTORS


def test_pvs_ai_returns_legal_move():
    board = parse_fen(STARTING_FEN)
    ai = PVSAI(time_limit_s=1.0, max_depth=1)

    move = ai.choose_move(board)

    assert move in generate_legal_moves(board, board.side_to_move)
    assert ai.last_result.depth == 1
    assert ai.last_result.nodes > 0


def test_pvs_ai_records_phase_used_for_time_budget():
    board = parse_fen(STARTING_FEN)
    ai = PVSAI(time_limit_s=1.0, max_depth=1)

    ai.choose_move(board)

    assert ai.last_phase == game_phase(board)
    assert ai.last_phase_budget == 1.0 * PHASE_FACTORS[ai.last_phase]
