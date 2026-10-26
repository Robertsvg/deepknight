"""
play.py

Small console game for Tablut.

Run with:
python -m src.play

Commands:
- b2-a2     play a move
- moves     show all legal moves
- fen       show current FEN
- ai        let the AI play one move
- random    play a random move
- selfplay  AI/random plays against itself
- quit      exit
"""

import random
import re

from src.ai import AdvancedAI
from src.board import WHITE, algebraic_to_coords, coords_to_algebraic
from src.fen import starting_position, to_fen
from src.moves import apply_move, generate_legal_moves
from src.rules import is_game_over


def side_name(side):
    if side == WHITE:
        return "White"

    return "Black"


def move_to_string(move):
    from_row, from_col, to_row, to_col = move

    start = coords_to_algebraic(from_row, from_col)
    target = coords_to_algebraic(to_row, to_col)

    return f"{start}-{target}"


def parse_move(text):
    """
    Converts text like b2-a2 into a move tuple.
    """

    text = text.strip().lower()

    match = re.fullmatch(r"([a-i][1-9])-([a-i][1-9])", text)
    if match is None:
        raise ValueError("Move must look like b2-a2")

    start, target = match.groups()

    from_row, from_col = algebraic_to_coords(start)
    to_row, to_col = algebraic_to_coords(target)

    return from_row, from_col, to_row, to_col


def show_board(board):
    print()
    print(board)
    print()
    print("FEN:", to_fen(board))

    result = is_game_over(board)

    if result is not None:
        print("Game over:", result)


def get_legal_moves(board):
    return list(generate_legal_moves(board, board.side_to_move))


def play_random_move(board):
    moves = get_legal_moves(board)

    if not moves:
        print("No legal moves.")
        return board

    move = random.choice(moves)

    print("Random move:", move_to_string(move))

    return apply_move(board, move)


def play_ai_move(board, ai):
    moves = get_legal_moves(board)

    if not moves:
        print("No legal moves.")
        return board

    move = ai.choose_move(board)

    if move not in moves:
        print("AI did not return a legal move.")
        return board

    print("AI move:", move_to_string(move))

    return apply_move(board, move)


def selfplay(board, ai, max_moves=100):
    print("Starting self-play...")

    for turn in range(1, max_moves + 1):
        result = is_game_over(board)

        if result is not None:
            show_board(board)
            print("Game over after", turn - 1, "plies:", result)
            return board

        moves = get_legal_moves(board)

        if not moves:
            show_board(board)
            print("No legal moves. Draw.")
            return board

        print()
        print("Ply", turn, "-", side_name(board.side_to_move))

        if ai is None:
            move = random.choice(moves)
        else:
            move = ai.choose_move(board)

        if move not in moves:
            print("No legal move returned.")
            return board

        print("Move:", move_to_string(move))

        board = apply_move(board, move)

    print("Self-play stopped after", max_moves, "plies.")
    return board


def print_moves(board):
    moves = get_legal_moves(board)

    print("Legal moves:", len(moves))

    for move in moves:
        print(move_to_string(move))


def make_ai():
    return AdvancedAI(time_limit_s=0.3, max_depth=3)


def main():
    board = starting_position()
    ai = make_ai()

    print("Tablut Console")
    print("Commands: b2-a2, moves, fen, ai, random, selfplay, quit")

    while True:
        show_board(board)

        result = is_game_over(board)

        if result is not None:
            print("Game over:", result)
            break

        try:
            command = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if command == "":
            continue

        if command in ("quit", "exit", "q"):
            break

        if command == "fen":
            print(to_fen(board))
            continue

        if command == "moves":
            print_moves(board)
            continue

        if command == "random":
            board = play_random_move(board)
            continue

        if command == "ai":
            board = play_ai_move(board, ai)
            continue

        if command == "selfplay":
            board = selfplay(board, ai, max_moves=30)
            continue

        try:
            move = parse_move(command)
        except ValueError as error:
            print("Invalid input:", error)
            continue

        legal_moves = get_legal_moves(board)

        if move not in legal_moves:
            print("Illegal move:", command)
            print("Enter 'moves' to see legal moves.")
            continue

        board = apply_move(board, move)


if __name__ == "__main__":
    main()
