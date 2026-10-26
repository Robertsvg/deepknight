"""Alpha-Beta-Suche fuer Tablut M2.

Wie minimax.py, aber mit Cutoffs:
- alpha = bisher garantierter Mindest-Score fuer Maximizer
- beta  = bisher zugelassener Hoechst-Score fuer Minimizer
- Wenn alpha >= beta: Cutoff (Rest ueberspringen)
"""

from typing import Optional

from src.board import WHITE, Board
from src.evaluation import evaluate, terminal_score
from src.move_ordering import order_moves
from src.moves import apply_move, generate_legal_moves

Move = Optional[tuple[int, int, int, int]]


def alpha_beta(
    board: Board,
    depth: int,
    alpha: float = float("-inf"),
    beta: float = float("+inf"),
) -> tuple[float, Move]:
    """Sucht den besten Zug mit Alpha-Beta-Cutoffs.

    Returns: (score, best_move)
    """
    score, move, _ = alpha_beta_with_count(board, depth, alpha, beta)
    return score, move


def alpha_beta_with_count(
    board: Board,
    depth: int,
    alpha: float = float("-inf"),
    beta: float = float("+inf"),
    counter: Optional[list] = None,
    plies_from_root: int = 0,
) -> tuple[float, Move, int]:
    """Wie alpha_beta, gibt aber zusaetzlich die Anzahl untersuchter Knoten zurueck.

    `plies_from_root` -> tiefenabhaengiger Sieg-Score:
    Schnelle Mattfuehrungen werden hoeher bewertet als spaete.

    Returns: (score, best_move, nodes)
    """
    if counter is None:
        counter = [0]

    counter[0] += 1

    term = terminal_score(board, plies_from_root)
    if term is not None:
        return term, None, counter[0]
    if depth == 0:
        return evaluate(board), None, counter[0]

    moves = order_moves(
        board, generate_legal_moves(board, board.side_to_move), depth=depth
    )

    if board.side_to_move == WHITE:
        best_score = float("-inf")
        best_move = None

        for move in moves:
            child = apply_move(board, move)
            score, _, _ = alpha_beta_with_count(
                child, depth - 1, alpha, beta, counter, plies_from_root + 1
            )

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, best_score)
            if alpha >= beta:
                break

        return best_score, best_move, counter[0]

    else:
        best_score = float("+inf")
        best_move = None

        for move in moves:
            child = apply_move(board, move)
            score, _, _ = alpha_beta_with_count(
                child, depth - 1, alpha, beta, counter, plies_from_root + 1
            )

            if score < best_score:
                best_score = score
                best_move = move

            beta = min(beta, best_score)
            if alpha >= beta:
                break

        return best_score, best_move, counter[0]
