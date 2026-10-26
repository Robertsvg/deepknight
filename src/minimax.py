"""Minimax-Algorithmus fuer Tablut M2.

Ohne Cutoffs (siehe alpha_beta.py fuer die optimierte Version).

Konvention: Score immer aus Sicht von WEISS.
- Hoher Score = gut fuer Weiss
- Niedriger Score = gut fuer Schwarz
- Weiss = Maximizer, Schwarz = Minimizer
"""

from typing import Optional

from src.board import WHITE, Board
from src.evaluation import evaluate, terminal_score
from src.moves import apply_move, generate_legal_moves

Move = Optional[tuple[int, int, int, int]]


def minimax(board: Board, depth: int) -> tuple[float, Move]:
    """Sucht den besten Zug fuer die Seite die am Zug ist.

    Returns: (score, best_move)
    """
    score, move, _ = minimax_with_count(board, depth)
    return score, move


def minimax_with_count(
    board: Board,
    depth: int,
    counter: Optional[list] = None,
    plies_from_root: int = 0,
) -> tuple[float, Move, int]:
    """Wie minimax, gibt aber zusaetzlich die Anzahl untersuchter Knoten zurueck.

    `plies_from_root` ist intern fuer tiefenabhaengige Siege:
    Schnelle Mattfuehrungen werden hoeher bewertet als spaete.

    Returns: (score, best_move, nodes)
    """
    if counter is None:
        counter = [0]

    counter[0] += 1

    # Terminale Stellung -> tiefenangepasster Sieg-Score (oder None).
    term = terminal_score(board, plies_from_root)
    if term is not None:
        return term, None, counter[0]
    if depth == 0:
        return evaluate(board), None, counter[0]

    moves = generate_legal_moves(board, board.side_to_move)

    if board.side_to_move == WHITE:
        best_score = float("-inf")
        best_move = None

        for move in moves:
            child = apply_move(board, move)
            score, _, _ = minimax_with_count(
                child, depth - 1, counter, plies_from_root + 1
            )

            if score > best_score:
                best_score = score
                best_move = move

        return best_score, best_move, counter[0]

    else:
        best_score = float("+inf")
        best_move = None

        for move in moves:
            child = apply_move(board, move)
            score, _, _ = minimax_with_count(
                child, depth - 1, counter, plies_from_root + 1
            )

            if score < best_score:
                best_score = score
                best_move = move

        return best_score, best_move, counter[0]
