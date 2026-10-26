"""Regression tests for UCT and RAVE search."""

import pytest

from src.ai import MCTSAI
from src.evaluation import WIN_SCORE
from src.fen import STARTING_FEN, parse_fen
from src.mcts import mcts, mcts_with_stats
from src.moves import generate_legal_moves


def assert_legal(board, move):
    assert move is not None
    assert move in generate_legal_moves(board, board.side_to_move)


def test_mcts_returns_legal_move_from_start_position():
    board = parse_fen(STARTING_FEN)

    result = mcts_with_stats(
        board,
        time_limit_s=None,
        max_iterations=30,
        rollout_depth=8,
        random_seed=1,
    )

    assert_legal(board, result.best_move)
    assert result.iterations == 30
    assert -WIN_SCORE <= result.score <= WIN_SCORE


def test_mcts_prefers_immediate_white_win():
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")

    score, move = mcts(
        board,
        time_limit_s=None,
        max_iterations=40,
        rollout_depth=6,
        random_seed=2,
    )

    assert move == (8, 1, 8, 0)
    assert score > 0


def test_mcts_prefers_immediate_black_win():
    board = parse_fen("9/9/9/9/9/9/9/rK1r5/9 s 0 1")

    score, move = mcts(
        board,
        time_limit_s=None,
        max_iterations=40,
        rollout_depth=6,
        random_seed=3,
    )

    assert move == (7, 3, 7, 2)
    assert score < 0


def test_mcts_terminal_root_returns_no_move():
    board = parse_fen("9/9/9/9/9/9/9/9/K8 w 0 1")

    result = mcts_with_stats(board, time_limit_s=None, max_iterations=20)

    assert result.best_move is None
    assert result.iterations == 0
    assert result.score == WIN_SCORE


def test_mcts_ai_matches_choose_move_interface():
    board = parse_fen(STARTING_FEN)
    ai = MCTSAI(
        time_limit_s=1.0,
        max_iterations=20,
        rollout_depth=6,
        random_seed=4,
    )

    move = ai.choose_move(board)

    assert_legal(board, move)
    assert ai.last_result is not None
    assert ai.last_result.iterations == 20


def test_mcts_collects_rave_statistics():
    """RAVE credits moves that appear anywhere in a simulation, not only the
    move that was actually selected, so children accumulate AMAF visits."""
    board = parse_fen(STARTING_FEN)

    root = _run_and_return_root(board, use_rave=True)

    rave_children = [child for child in root.children if child.rave_visits > 0]
    assert rave_children, "no child received AMAF credit"
    # AMAF sees far more samples than plain visits.
    assert max(c.rave_visits for c in root.children) >= max(
        c.visits for c in root.children
    )


def test_mcts_without_rave_keeps_amaf_statistics_empty():
    board = parse_fen(STARTING_FEN)
    root = _run_and_return_root(board, use_rave=False)
    assert root.visits == 60
    assert all(child.rave_visits == 0 for child in root.children)


def _run_and_return_root(board, use_rave):
    """Rebuild a small search tree so the test can inspect node statistics."""
    import math
    import random

    from src.mcts import MCTSNode, _backpropagate, _expand, _rollout, _select

    root = MCTSNode(board.copy())
    rng = random.Random(7)
    root.legal_untried_moves()
    for _ in range(60):
        path = _select(root, math.sqrt(2.0), use_rave)
        leaf = _expand(path[-1])
        if leaf is not path[-1]:
            path.append(leaf)
        value, rollout_moves = _rollout(leaf.board, rng, 8)
        _backpropagate(path, value, rollout_moves, use_rave=use_rave)
    return root


def test_mcts_ai_can_disable_rave(monkeypatch):
    from src import ai as ai_module
    from src.mcts import MCTSResult

    board = parse_fen(STARTING_FEN)
    move = next(iter(generate_legal_moves(board, board.side_to_move)))
    calls = []

    def search(position, **options):
        calls.append(options)
        return MCTSResult(0.0, move, 1, 0.0)

    monkeypatch.setattr(ai_module, "mcts_with_stats", search)
    ai = MCTSAI(use_rave=False)
    assert ai.choose_move(board) == move
    assert calls[0]["use_rave"] is False


def test_zero_budget_returns_legal_move_without_rollout(monkeypatch):
    from src import mcts as mcts_module

    board = parse_fen(STARTING_FEN)

    def unexpected_rollout(*args, **kwargs):
        pytest.fail("a spent time budget must not start a rollout")

    monkeypatch.setattr(mcts_module, "_rollout", unexpected_rollout)
    result = mcts_with_stats(board, time_limit_s=0.0)
    assert result.iterations == 0
    assert_legal(board, result.best_move)


def test_rollout_observes_deadline_before_generating_moves(monkeypatch):
    import random

    from src import mcts as mcts_module

    board = parse_fen(STARTING_FEN)
    monkeypatch.setattr(mcts_module.time, "monotonic", lambda: 10.0)

    def unexpected_generation(*args):
        pytest.fail("an expired rollout must not generate another move")

    monkeypatch.setattr(mcts_module, "generate_legal_moves", unexpected_generation)
    value, moves = mcts_module._rollout(board, random.Random(1), 80, deadline=9.0)
    assert -1.0 <= value <= 1.0
    assert moves == []


@pytest.mark.parametrize(
    "options",
    [
        {"time_limit_s": -1},
        {"time_limit_s": float("nan")},
        {"max_iterations": -1},
        {"rollout_depth": -1},
        {"exploration": -1},
    ],
)
def test_mcts_rejects_invalid_budgets(options):
    with pytest.raises(ValueError):
        mcts_with_stats(parse_fen(STARTING_FEN), **options)


@pytest.mark.parametrize("side", ["w", "s"])
def test_rave_changes_selection_using_the_correct_player_perspective(side):
    from src.board import WHITE
    from src.mcts import MCTSNode, _uct_child

    board = parse_fen(f"9/9/9/9/4K4/9/3r5/9/9 {side} 0 1")
    root = MCTSNode(board)
    moves = list(generate_legal_moves(board, board.side_to_move))
    first, second = (root.add_child(move) for move in moves[:2])
    sign = 1 if board.side_to_move == WHITE else -1
    root.visits = 2
    for child, direct, amaf in ((first, 0.9, 0.0), (second, 0.1, 1.0)):
        child.visits = 1
        child.total_value = sign * direct
        child.rave_visits = 10
        child.rave_value = 10 * sign * amaf

    assert _uct_child(root, exploration=0.0, use_rave=False) is first
    assert _uct_child(root, exploration=0.0, use_rave=True) is second
