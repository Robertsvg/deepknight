"""
iterative_deepening.py

Runs search with depth 1, 2, 3, ...
Only the last completely finished depth is used.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class IterativeDeepeningResult:
    depth: int
    score: Optional[float]
    best_move: Any
    nodes: int
    elapsed: float


def iterative_deepening(board, search_fn, time_manager, max_depth=None):

    depth = 1

    best_score = None
    best_move = None
    best_depth = 0
    best_nodes = 0

    while time_manager.time_left():
        if max_depth is not None and depth > max_depth:
            break

        try:
            result = search_fn(board, depth, time_manager)
        except TimeoutError:
            break

        if not time_manager.time_left():
            break

        if len(result) == 2:
            score, move = result
            nodes = 0
        else:
            score, move, nodes = result

        best_score = score
        best_move = move
        best_depth = depth
        best_nodes = nodes

        depth += 1

    return IterativeDeepeningResult(
        depth=best_depth,
        score=best_score,
        best_move=best_move,
        nodes=best_nodes,
        elapsed=time_manager.elapsed(),
    )
