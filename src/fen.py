"""FEN-Parser für Tablut.

FEN-Format: <reihen> <zug> <halbzüge_ohne_schlag> <vollzug>
Beispiel: "9/9/9/9/9/9/3r5/1K7/9 w 0 1"

Reihen: 9 Reihen getrennt durch '/', von oben (Reihe 9) nach unten (Reihe 1).
Innerhalb einer Reihe: Zahl = leere Felder, Buchstabe = Figur (r/R/K).
"""

from src.board import ATTACKER, BLACK, DEFENDER, EMPTY, KING, WHITE, Board

VALID_PIECES = {ATTACKER, DEFENDER, KING}


def parse_fen(fen_string):
    parts = fen_string.strip().split()
    if len(parts) < 2:
        raise ValueError(f"FEN braucht mindestens Brett und Zug-Info: {fen_string}")

    board_part = parts[0]
    side = parts[1].lower()
    halfmoves = int(parts[2]) if len(parts) > 2 else 0
    fullmove = int(parts[3]) if len(parts) > 3 else 1

    rows = board_part.split("/")
    if len(rows) != 9:
        raise ValueError(f"FEN braucht 9 Reihen, gefunden: {len(rows)}")

    board = Board()
    for row_idx, row_str in enumerate(rows):
        col = 0
        for char in row_str:
            if char.isdigit():
                col += int(char)
            elif char in VALID_PIECES:
                if col >= 9:
                    raise ValueError(f"Reihe {9 - row_idx} zu lang: {row_str}")
                board.set(row_idx, col, char)
                col += 1
            else:
                raise ValueError(f"Ungültiges Zeichen '{char}' in Reihe {9 - row_idx}")
        if col != 9:
            raise ValueError(
                f"Reihe {9 - row_idx} hat {col} Felder, erwartet 9: {row_str}"
            )

    if side not in (WHITE, BLACK):
        raise ValueError(f"Zug muss 'w' oder 's' sein: {side}")
    board.side_to_move = side
    board.halfmoves_no_capture = halfmoves
    board.fullmove_number = fullmove

    king_pos = board.find_king()
    if king_pos and king_pos != (4, 4):
        board.king_left_throne = True

    return board


def to_fen(board):
    rows = []
    for row in range(9):
        row_str = ""
        empty_count = 0
        for col in range(9):
            piece = board.get(row, col)
            if piece == EMPTY:
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += piece
        if empty_count > 0:
            row_str += str(empty_count)
        rows.append(row_str)

    return f"{'/'.join(rows)} {board.side_to_move} {board.halfmoves_no_capture} {board.fullmove_number}"


STARTING_FEN = "3rrr3/4r4/4R4/r3R3r/rrRRKRRrr/r3R3r/4R4/4r4/3rrr3 s 0 1"


def starting_position():
    return parse_fen(STARTING_FEN)
