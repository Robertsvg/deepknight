"""
perft.py

Used to test the move generator.

perft(board, 0) = 1
perft(board, 1) = number of legal moves
perft(board, 2) = number of legal move sequences
"""

from src.board import coords_to_algebraic
from src.fen import parse_fen
from src.moves import apply_move, generate_legal_moves
from src.rules import is_game_over


def move_to_string(move):
    """Turns a move into text like b2-a2."""

    if isinstance(move, str):
        return move

    if isinstance(move, (tuple, list)):
        if len(move) == 4:
            from_row, from_col, to_row, to_col = move
            start = coords_to_algebraic(from_row, from_col)
            target = coords_to_algebraic(to_row, to_col)
            return f"{start}-{target}"

        if len(move) == 2:
            start_pos, target_pos = move
            start = coords_to_algebraic(start_pos[0], start_pos[1])
            target = coords_to_algebraic(target_pos[0], target_pos[1])
            return f"{start}-{target}"

    if hasattr(move, "from_row") and hasattr(move, "from_col"):
        start = coords_to_algebraic(move.from_row, move.from_col)
        target = coords_to_algebraic(move.to_row, move.to_col)
        return f"{start}-{target}"

    return str(move)


def perft(board, depth):
    """Counts all legal move sequences up to the given depth."""

    if depth < 0:
        raise ValueError("depth cannot be negative")

    if depth == 0:
        return 1

    if is_game_over(board) is not None:
        return 0

    moves = list(generate_legal_moves(board, board.side_to_move))

    if depth == 1:
        return len(moves)

    total = 0

    for move in moves:
        child = apply_move(board, move)
        total += perft(child, depth - 1)

    return total


def divide(board, depth):
    """Shows how many positions each move creates."""

    if depth <= 0:
        return [], 1

    if is_game_over(board) is not None:
        return [], 0

    results = []
    total = 0

    moves = list(generate_legal_moves(board, board.side_to_move))

    for move in moves:
        child = apply_move(board, move)
        count = perft(child, depth - 1)

        results.append((move_to_string(move), count))
        total += count

    return results, total


def print_divide(board, depth):
    results, total = divide(board, depth)

    for move_text, count in results:
        print(f"{move_text}: {count}")

    print(f"Total: {total}")


def run_perft(fen_string, max_depth=3):
    board = parse_fen(fen_string)

    print(board)
    print()

    for depth in range(1, max_depth + 1):
        print(f"Perft({depth}) = {perft(board, depth)}")


if __name__ == "__main__":
    fen = "9/9/9/9/9/9/3r5/1K7/9 w 0 1"

    run_perft(fen, 3)

    print()
    print("Divide depth 1:")

    board = parse_fen(fen)
    print_divide(board, 1)
