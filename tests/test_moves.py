"""Tests fuer Zuggenerator und Zugausfuehrung."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.board import ATTACKER, BLACK, EMPTY, KING, THRONE, WHITE
from src.fen import STARTING_FEN, parse_fen
from src.moves import apply_move, generate_legal_moves


def test_stellung_1_koenigsflucht():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    moves = generate_legal_moves(board, WHITE)
    assert len(moves) == 16, f"Erwartete 16 Zuege, bekam {len(moves)}"


def test_stellung_2_sandwichfalle():
    board = parse_fen("9/9/9/2r6/2R6/r8/9/9/9 s 0 1")
    moves = generate_legal_moves(board, BLACK)
    assert len(moves) == 25, f"Erwartete 25 Zuege, bekam {len(moves)}"


def test_startstellung_schwarz():
    board = parse_fen(STARTING_FEN)
    moves = generate_legal_moves(board, BLACK)
    assert len(moves) == 72


def test_startstellung_weiss():
    board = parse_fen(STARTING_FEN)
    moves = generate_legal_moves(board, WHITE)
    assert len(moves) == 56


def test_schwarz_darf_nicht_auf_eckfeld():
    board = parse_fen("9/9/9/9/9/r8/9/9/9 s 0 1")
    moves = generate_legal_moves(board, BLACK)
    assert (5, 0, 8, 0) not in moves
    assert (5, 0, 0, 0) not in moves


def test_schwarz_darf_nicht_auf_thron_aber_darueber_hinweg():
    board = parse_fen("9/9/9/9/r8/9/9/9/9 s 0 1")
    moves = generate_legal_moves(board, BLACK)
    assert (4, 0, 4, 4) not in moves
    assert (4, 0, 4, 5) in moves
    assert (4, 0, 4, 8) in moves


def test_koenig_darf_nach_verlassen_nicht_zurueck_auf_thron():
    board = parse_fen("9/9/9/9/3K5/9/9/9/9 w 0 1")
    moves = generate_legal_moves(board, WHITE)
    assert board.king_left_throne is True
    assert (4, 3, 4, 4) not in moves
    assert (4, 3, 4, 5) in moves


def test_figuren_duerfen_nicht_uebersprungen_werden():
    board = parse_fen("9/9/9/9/rR7/9/9/9/9 s 0 1")
    moves = generate_legal_moves(board, BLACK)
    assert (4, 0, 4, 1) not in moves
    assert (4, 0, 4, 2) not in moves


def test_apply_move_aendert_original_nicht():
    board = parse_fen("9/9/9/9/9/9/9/1K7/9 w 7 3")
    new_board = apply_move(board, (7, 1, 7, 2))

    assert board.get(7, 1) == KING
    assert board.get(7, 2) == EMPTY
    assert board.side_to_move == WHITE
    assert board.halfmoves_no_capture == 7
    assert board.fullmove_number == 3

    assert new_board.get(7, 1) == EMPTY
    assert new_board.get(7, 2) == KING
    assert new_board.side_to_move == BLACK
    assert new_board.halfmoves_no_capture == 8
    assert new_board.fullmove_number == 4


def test_apply_move_setzt_king_left_throne():
    board = parse_fen("9/9/9/9/4K4/9/9/9/9 w 0 1")
    new_board = apply_move(board, (THRONE[0], THRONE[1], 4, 5))
    assert new_board.king_left_throne is True


def test_apply_move_entfernt_geschlagene_figuren():
    board = parse_fen("9/9/9/2r6/2R6/r8/9/9/9 s 12 4")
    new_board = apply_move(board, (5, 0, 5, 2))

    assert new_board.get(5, 2) == ATTACKER
    assert new_board.get(4, 2) == EMPTY
    assert new_board.halfmoves_no_capture == 0
    assert new_board.side_to_move == WHITE
    assert new_board.fullmove_number == 4


def test_apply_move_erhoeht_vollzug_nach_weiss():
    board = parse_fen("9/9/9/9/9/9/9/1K7/9 w 0 1")
    new_board = apply_move(board, (7, 1, 7, 2))
    assert new_board.side_to_move == BLACK
    assert new_board.fullmove_number == 2


def test_apply_move_lehnt_blockierten_pfad_ab():
    board = parse_fen("9/9/9/9/rR7/9/9/9/9 s 0 1")
    with pytest.raises(ValueError):
        apply_move(board, (4, 0, 4, 2))


def test_apply_move_lehnt_diagonalen_zug_ab():
    board = parse_fen("9/9/9/9/9/9/9/1K7/9 w 0 1")
    with pytest.raises(ValueError):
        apply_move(board, (7, 1, 6, 2))


def test_apply_move_lehnt_falsche_seite_ab():
    board = parse_fen("9/9/9/9/9/9/9/1K7/r8 w 0 1")
    with pytest.raises(ValueError):
        apply_move(board, (8, 0, 8, 1))


if __name__ == "__main__":
    test_stellung_1_koenigsflucht()
    test_stellung_2_sandwichfalle()
    test_startstellung_schwarz()
    test_startstellung_weiss()
    test_schwarz_darf_nicht_auf_eckfeld()
    test_schwarz_darf_nicht_auf_thron_aber_darueber_hinweg()
    test_koenig_darf_nach_verlassen_nicht_zurueck_auf_thron()
    test_figuren_duerfen_nicht_uebersprungen_werden()
    test_apply_move_aendert_original_nicht()
    test_apply_move_setzt_king_left_throne()
    test_apply_move_entfernt_geschlagene_figuren()
    test_apply_move_erhoeht_vollzug_nach_weiss()
    test_apply_move_lehnt_blockierten_pfad_ab()
    test_apply_move_lehnt_diagonalen_zug_ab()
    test_apply_move_lehnt_falsche_seite_ab()
    print("Alle Move-Tests bestanden.")
