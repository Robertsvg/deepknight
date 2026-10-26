"""Tests für FEN-Parser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.board import ATTACKER, BLACK, DEFENDER, WHITE
from src.fen import STARTING_FEN, parse_fen, to_fen


def test_starting_position():
    board = parse_fen(STARTING_FEN)
    assert board.find_king() == (4, 4), "König muss auf e5 (Thron) stehen"
    assert board.side_to_move == BLACK, "Schwarz beginnt"
    assert board.king_left_throne is False


def test_stellung_1_koenigsflucht():
    """Unsere TubCloud Stellung 1: König auf b2."""
    fen = "9/9/9/9/9/9/3r5/1K7/9 w 0 1"
    board = parse_fen(fen)
    assert board.find_king() == (7, 1), "König muss auf b2 sein (row=7, col=1)"
    assert board.get(6, 3) == ATTACKER, "Schwarze Figur muss auf d3 sein"
    assert board.side_to_move == WHITE
    assert board.king_left_throne is True, "König hat Thron verlassen"


def test_stellung_2_sandwichfalle():
    """Unsere TubCloud Stellung 2."""
    fen = "9/9/9/2r6/2R6/r8/9/9/9 s 0 1"
    board = parse_fen(fen)
    assert board.get(3, 2) == ATTACKER, "r auf c6"
    assert board.get(4, 2) == DEFENDER, "R auf c5"
    assert board.get(5, 0) == ATTACKER, "r auf a4"
    assert board.side_to_move == BLACK


def test_roundtrip():
    """FEN -> Board -> FEN muss identisch sein."""
    test_fens = [
        STARTING_FEN,
        "9/9/9/9/9/9/3r5/1K7/9 w 0 1",
        "9/9/9/2r6/2R6/r8/9/9/9 s 0 1",
    ]
    for fen in test_fens:
        board = parse_fen(fen)
        assert to_fen(board) == fen, f"Roundtrip fehlgeschlagen für: {fen}"


if __name__ == "__main__":
    test_starting_position()
    test_stellung_1_koenigsflucht()
    test_stellung_2_sandwichfalle()
    test_roundtrip()
    print("Alle FEN-Tests bestanden.")
