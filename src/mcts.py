"""Monte Carlo Tree Search with optional UCT/RAVE selection for Tablut.

Scores and rollout values follow the project convention:
- positive values are good for White
- negative values are good for Black

The implementation is deliberately single-threaded. It is meant as a
complementary technique next to the Alpha-Beta/PVS stack, not as a
replacement for the contest-proven AdvancedAI.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Optional

from src.board import BLACK, WHITE, Board
from src.evaluation import WIN_SCORE, evaluate, terminal_score
from src.move_ordering import order_moves
from src.moves import apply_move, generate_legal_moves

Move = tuple[int, int, int, int]

# Controls how quickly the AMAF contribution decays with direct visits.
RAVE_K = 300.0


@dataclass
class MCTSResult:
    """Result object returned by MCTS searches."""

    score: float
    best_move: Optional[Move]
    iterations: int
    elapsed: float


class MCTSNode:
    """One node in the MCTS tree."""

    __slots__ = (
        "board",
        "parent",
        "move",
        "children",
        "untried_moves",
        "visits",
        "total_value",
        "rave_visits",
        "rave_value",
    )

    def __init__(
        self,
        board: Board,
        parent: Optional["MCTSNode"] = None,
        move: Optional[Move] = None,
    ) -> None:
        self.board = board
        self.parent = parent
        self.move = move
        self.children: list[MCTSNode] = []
        self.untried_moves: Optional[list[Move]] = None
        self.visits = 0
        self.total_value = 0.0
        # AMAF statistics: how often this node's move was played anywhere in a
        # simulation that started at the parent, and with which outcome.
        self.rave_visits = 0
        self.rave_value = 0.0

    @property
    def average_value(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_value / self.visits

    @property
    def rave_average(self) -> float:
        if self.rave_visits == 0:
            return 0.0
        return self.rave_value / self.rave_visits

    def legal_untried_moves(self) -> list[Move]:
        if self.untried_moves is None:
            moves = list(generate_legal_moves(self.board, self.board.side_to_move))
            # Keep the best move at the end for constant-time expansion.
            self.untried_moves = list(reversed(order_moves(self.board, moves)))
        return self.untried_moves

    def is_fully_expanded(self) -> bool:
        return not self.legal_untried_moves()

    def add_child(self, move: Move) -> "MCTSNode":
        child = MCTSNode(apply_move(self.board, move), parent=self, move=move)
        self.children.append(child)
        return child


def mcts(
    board: Board,
    time_limit_s: Optional[float] = 1.0,
    max_iterations: Optional[int] = None,
    exploration: float = math.sqrt(2.0),
    rollout_depth: int = 80,
    random_seed: Optional[int] = None,
    use_rave: bool = True,
) -> tuple[float, Optional[Move]]:
    """Run MCTS and return (score, best_move)."""
    result = mcts_with_stats(
        board,
        time_limit_s=time_limit_s,
        max_iterations=max_iterations,
        exploration=exploration,
        rollout_depth=rollout_depth,
        random_seed=random_seed,
        use_rave=use_rave,
    )
    return result.score, result.best_move


def mcts_with_stats(
    board: Board,
    time_limit_s: Optional[float] = 1.0,
    max_iterations: Optional[int] = None,
    exploration: float = math.sqrt(2.0),
    rollout_depth: int = 80,
    random_seed: Optional[int] = None,
    use_rave: bool = True,
) -> MCTSResult:
    """Run single-threaded UCT search and return score, move, and statistics.

    Args:
        board: Root position.
        time_limit_s: Wall-clock budget. Pass None to rely only on
            ``max_iterations``.
        max_iterations: Optional deterministic iteration cap.
        exploration: UCT exploration constant.
        rollout_depth: Maximum rollout plies before falling back to evaluate().
        random_seed: Optional seed for reproducible tests.
        use_rave: Blend the AMAF/RAVE estimate into move selection. Disable to
            fall back to plain UCT (used for A/B comparisons).
    """
    if time_limit_s is not None and (
        not math.isfinite(time_limit_s) or time_limit_s < 0
    ):
        raise ValueError("time_limit_s must be finite and non-negative")
    if max_iterations is not None and max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")
    if rollout_depth < 0:
        raise ValueError("rollout_depth must be non-negative")
    if not math.isfinite(exploration) or exploration < 0:
        raise ValueError("exploration must be finite and non-negative")

    start = time.monotonic()
    deadline = None if time_limit_s is None else start + max(0.0, time_limit_s)
    if max_iterations is None:
        max_iterations = 1_000 if time_limit_s is None else 10**9

    root = MCTSNode(board.copy())
    rng = random.Random(random_seed)

    terminal = terminal_score(root.board, 0)
    if terminal is not None:
        return MCTSResult(terminal, None, 0, time.monotonic() - start)

    root_moves = root.legal_untried_moves()
    if not root_moves:
        return MCTSResult(evaluate(root.board), None, 0, time.monotonic() - start)

    iterations = 0
    while iterations < max_iterations:
        if deadline is not None and time.monotonic() >= deadline:
            break

        path = _select(root, exploration, use_rave)
        leaf = _expand(path[-1])
        if leaf is not path[-1]:
            path.append(leaf)
        value, rollout_moves = _rollout(
            leaf.board,
            rng,
            rollout_depth,
            deadline=deadline,
            collect_amaf=use_rave,
        )
        _backpropagate(path, value, rollout_moves, use_rave=use_rave)
        iterations += 1

    if iterations == 0:
        move = root_moves[-1]
        child = apply_move(root.board, move)
        score = terminal_score(child, 1)
        if score is None:
            score = evaluate(child)
        return MCTSResult(score, move, 0, time.monotonic() - start)

    best_child = _best_root_child(root)
    if best_child is None:
        return MCTSResult(
            evaluate(root.board), None, iterations, time.monotonic() - start
        )

    return MCTSResult(
        _score_from_value(best_child.average_value),
        best_child.move,
        iterations,
        time.monotonic() - start,
    )


def _select(node: MCTSNode, exploration: float, use_rave: bool) -> list[MCTSNode]:
    """Descend the tree and return the visited path from root to leaf."""
    path = [node]
    while terminal_score(node.board, 0) is None and node.is_fully_expanded():
        if not node.children:
            break
        node = _uct_child(node, exploration, use_rave)
        path.append(node)
    return path


def _expand(node: MCTSNode) -> MCTSNode:
    if terminal_score(node.board, 0) is not None:
        return node

    untried = node.legal_untried_moves()
    if not untried:
        return node

    move = untried.pop()
    return node.add_child(move)


def _uct_child(node: MCTSNode, exploration: float, use_rave: bool) -> MCTSNode:
    log_parent = math.log(max(node.visits, 1))
    side = node.board.side_to_move
    sign = 1.0 if side == WHITE else -1.0

    def uct_score(child: MCTSNode) -> float:
        if child.visits == 0:
            return float("inf")
        # Values are stored from White's perspective. White maximizes,
        # Black minimizes; use the sign in selection rather than duplicating
        # node statistics per player.
        exploitation = sign * child.average_value
        if use_rave and child.rave_visits > 0:
            # Gelly/Silver schedule: beta starts near 1 (trust the cheap AMAF
            # estimate) and decays towards 0 as real visits accumulate.
            beta = math.sqrt(RAVE_K / (3.0 * child.visits + RAVE_K))
            exploitation = (
                1.0 - beta
            ) * exploitation + beta * sign * child.rave_average
        exploration_term = exploration * math.sqrt(log_parent / child.visits)
        return exploitation + exploration_term

    return max(node.children, key=uct_score)


def _rollout(
    board: Board,
    rng: random.Random,
    rollout_depth: int,
    *,
    deadline: Optional[float] = None,
    collect_amaf: bool = True,
) -> tuple[float, list[tuple[str, Move]]]:
    """Simulate to the end and return the value plus every (side, move) played.

    The move list feeds the RAVE/AMAF statistics: each move is credited with
    the outcome of the whole simulation it appeared in.
    """
    current = board.copy()
    played: list[tuple[str, Move]] = []

    for ply in range(rollout_depth + 1):
        term = terminal_score(current, ply)
        if term is not None:
            return _value_from_score(term), played

        if ply == rollout_depth or (
            deadline is not None and time.monotonic() >= deadline
        ):
            return _value_from_score(evaluate(current)), played

        moves = list(generate_legal_moves(current, current.side_to_move))
        if not moves:
            return _value_from_score(evaluate(current)), played

        ordered = order_moves(current, moves)
        move = _rollout_move(current, ordered, rng)
        if collect_amaf:
            played.append((current.side_to_move, move))
        current = apply_move(current, move)

    return _value_from_score(evaluate(current)), played


def _rollout_move(board: Board, ordered_moves: list[Move], rng: random.Random) -> Move:
    """Choose a rollout move, preferring immediate wins and strong heuristics."""
    for move in ordered_moves[:8]:
        result = terminal_score(apply_move(board, move), 1)
        if result is None:
            continue
        if board.side_to_move == WHITE and result > 0:
            return move
        if board.side_to_move == BLACK and result < 0:
            return move

    candidate_count = min(4, len(ordered_moves))
    return rng.choice(ordered_moves[:candidate_count])


def _backpropagate(
    path: list[MCTSNode],
    value: float,
    rollout_moves: list[tuple[str, Move]],
    *,
    use_rave: bool = True,
) -> None:
    """Update visit statistics along the path and the AMAF statistics per side.

    Walking the path backwards keeps one move set per side. Every child whose
    move still occurs later in the simulation - by the side that is to move at
    that node - receives an AMAF credit, even though it was never selected.
    """
    if not use_rave:
        for node in path:
            node.visits += 1
            node.total_value += value
        return

    white_moves = {m for side, m in rollout_moves if side == WHITE}
    black_moves = {m for side, m in rollout_moves if side == BLACK}

    for index in range(len(path) - 1, -1, -1):
        node = path[index]
        node.visits += 1
        node.total_value += value

        side_moves = white_moves if node.board.side_to_move == WHITE else black_moves
        if side_moves:
            for child in node.children:
                if child.move in side_moves:
                    child.rave_visits += 1
                    child.rave_value += value

        # The move leading into this node was played by the parent's side.
        if index > 0 and node.move is not None:
            parent_side = path[index - 1].board.side_to_move
            target = white_moves if parent_side == WHITE else black_moves
            target.add(node.move)


def _best_root_child(root: MCTSNode) -> Optional[MCTSNode]:
    if not root.children:
        return None

    side = root.board.side_to_move

    def key(child: MCTSNode) -> tuple[int, float]:
        average = child.average_value
        oriented = average if side == WHITE else -average
        return child.visits, oriented

    return max(root.children, key=key)


def _value_from_score(score: float) -> float:
    return max(-1.0, min(1.0, score / WIN_SCORE))


def _score_from_value(value: float) -> float:
    return max(-WIN_SCORE, min(WIN_SCORE, value * WIN_SCORE))
