from src.fen import parse_fen
from src.perft import divide, perft


def test_perft_depth_0():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")

    assert perft(board, 0) == 1


def test_perft_simple_king_position_depth_1():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")

    assert perft(board, 1) == 16


def test_divide_sum_equals_perft():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")

    results, total = divide(board, 1)

    assert total == perft(board, 1)
    assert len(results) == 16


def test_stellung_1_perft_1():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    assert perft(board, 1) == 16


def test_stellung_2_perft_1():
    board = parse_fen("9/9/9/2r6/2R6/r8/9/1K7/9 s 0 1")
    assert perft(board, 1) == 25
