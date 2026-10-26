"""Zuggenerator und Zugausfuehrung fuer Tablut."""

from src.board import (
    ATTACKER,
    BLACK,
    DEFENDER,
    EMPTY,
    KING,
    THRONE,
    WHITE,
)

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def piece_belongs_to_side(piece, side):
    """Gibt True zurueck, wenn `piece` zur Seite `side` gehoert."""
    if side == BLACK:
        return piece == ATTACKER
    if side == WHITE:
        return piece in (DEFENDER, KING)
    raise ValueError(f"Ungueltige Seite: {side}")


def can_enter_square(board, piece, row, col):
    """Prueft, ob `piece` auf dem Zielfeld landen darf."""
    if board.is_corner(row, col):
        return piece == KING
    if board.is_throne(row, col):
        return piece == KING and not board.king_left_throne
    return True


def path_is_clear(board, from_row, from_col, to_row, to_col):
    """Prueft, ob ein orthogonaler Zug unterwegs keine Figur ueberspringt."""
    row_delta = to_row - from_row
    col_delta = to_col - from_col
    if row_delta != 0 and col_delta != 0:
        return False
    if row_delta == 0 and col_delta == 0:
        return False

    row_step = 0 if row_delta == 0 else row_delta // abs(row_delta)
    col_step = 0 if col_delta == 0 else col_delta // abs(col_delta)

    row = from_row + row_step
    col = from_col + col_step
    while (row, col) != (to_row, to_col):
        if not board.is_empty(row, col):
            return False
        row += row_step
        col += col_step
    return True


def generate_legal_moves(board, side):
    """Gibt alle legalen Zuege fuer `side` zurueck.

    Rueckgabe: Liste von Move-Tupeln:
    [(from_row, from_col, to_row, to_col), ...]
    """
    if side not in (WHITE, BLACK):
        raise ValueError(f"Ungueltige Seite: {side}")

    moves = []
    for row in range(9):
        for col in range(9):
            piece = board.get(row, col)
            if not piece_belongs_to_side(piece, side):
                continue

            for dr, dc in DIRECTIONS:
                next_row = row + dr
                next_col = col + dc

                while board.in_bounds(next_row, next_col):
                    if not board.is_empty(next_row, next_col):
                        break

                    if can_enter_square(board, piece, next_row, next_col):
                        moves.append((row, col, next_row, next_col))

                    next_row += dr
                    next_col += dc

    return moves


def apply_move(board, move):
    """Wendet `move` auf einer Brettkopie an und gibt das neue Brett zurueck."""
    from src.rules import check_captures

    from_row, from_col, to_row, to_col = move
    if not board.in_bounds(from_row, from_col) or not board.in_bounds(to_row, to_col):
        raise ValueError(f"Zug ausserhalb des Bretts: {move}")

    piece = board.get(from_row, from_col)
    if piece == EMPTY:
        raise ValueError(f"Kein Stein auf dem Startfeld: {move}")
    if not piece_belongs_to_side(piece, board.side_to_move):
        raise ValueError(f"Figur gehoert nicht zur Seite am Zug: {move}")
    if not board.is_empty(to_row, to_col):
        raise ValueError(f"Zielfeld ist besetzt: {move}")
    if not path_is_clear(board, from_row, from_col, to_row, to_col):
        raise ValueError(f"Zug ist nicht gerade oder Pfad ist blockiert: {move}")
    if not can_enter_square(board, piece, to_row, to_col):
        raise ValueError(f"Figur darf Zielfeld nicht betreten: {move}")

    new_board = board.copy()
    new_board.set(from_row, from_col, EMPTY)
    new_board.set(to_row, to_col, piece)

    if piece == KING and (from_row, from_col) == THRONE:
        new_board.king_left_throne = True

    captures = check_captures(new_board, (to_row, to_col))
    for cap_row, cap_col in captures:
        new_board.set(cap_row, cap_col, EMPTY)

    if captures:
        new_board.halfmoves_no_capture = 0
    else:
        new_board.halfmoves_no_capture += 1

    new_board.side_to_move = BLACK if board.side_to_move == WHITE else WHITE
    if new_board.side_to_move == BLACK:
        new_board.fullmove_number += 1

    return new_board
