from src.fen import parse_fen
from src.move_ordering import move_to_string, order_moves
from src.moves import generate_legal_moves


def test_capture_move_is_ordered_first():
    # b5 = defender, c5 = attacker, f5 = defender
    # White can move f5-d5 and capture c5.
    board = parse_fen("9/9/9/9/1Rr2R3/9/9/1K7/9 w 0 1")

    capture = (4, 5, 4, 3)  # f5-d5 schlaegt c5
    quiet = (7, 1, 7, 2)  # b2-c2 normaler Koenigszug

    # Beide Zuege muessen wirklich legal sein -- sonst testet die Sortierung
    # eine erfundene Position.
    legal = generate_legal_moves(board, board.side_to_move)
    assert capture in legal, "Test-Schlagzug ist nicht legal"
    assert quiet in legal, "Test-Ruhezug ist nicht legal"

    ordered = order_moves(board, [capture, quiet])

    assert ordered[0] == capture


def test_king_corner_move_is_ordered_first():
    # King on a2 can move to a1, which is a corner.
    board = parse_fen("9/9/9/9/9/9/9/K8/9 w 0 1")

    quiet = (7, 0, 7, 1)  # a2-b2
    corner = (7, 0, 8, 0)  # a2-a1 (Ecke)

    legal = generate_legal_moves(board, board.side_to_move)
    assert quiet in legal, "Test-Ruhezug ist nicht legal"
    assert corner in legal, "Test-Eckzug ist nicht legal"

    ordered = order_moves(board, [quiet, corner])

    assert ordered[0] == corner


def test_move_to_string():
    assert move_to_string((7, 1, 7, 0)) == "b2-a2"
