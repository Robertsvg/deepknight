"""Server-treue Schlag-/Zuglogik fuer die Contest-Anbindung.

Der TU-Gameserver (Gameserver25) hat eigenwillige Schlagregeln am Thron, die
sich von unseren internen Regeln (src/rules.py) unterscheiden. Damit das vom
Gameserver-Client gepflegte Brett IMMER exakt dem Server-Brett entspricht
(sonst Desync -> illegaler Zug -> verloren), bilden wir hier die Server-Logik
1:1 nach -- portiert aus gameserver/games/tablut.py:

  _check_for_captures():
    attacker = bewegte Figur (Koenig zaehlt als WEISS)
    je Richtung d: enemy = to+d, associate = to+2d
    expected_enemy = SCHWARZ wenn attacker WEISS, sonst WEISS
    (1) associate == attacker und enemy == expected_enemy        -> Schlag
    (2) leerer Thron als associate und enemy == expected_enemy   -> Schlag
    (3) associate_pos == Thron und enemy == SCHWARZ (immer!)     -> Schlag
    (4) associate_pos in Ecken und enemy == expected_enemy       -> Schlag

Diese Logik wird NUR vom Gameserver-Client benutzt, nicht von der KI-Suche.
"""

from __future__ import annotations

from src.board import (
    ATTACKER,
    BLACK,
    CORNERS,
    DEFENDER,
    EMPTY,
    KING,
    THRONE,
    WHITE,
)

# Reihenfolge egal fuer Schlagerkennung; entspricht ALIGNMENT_VECTORS des Servers.
_ALIGN = [(0, -1), (0, 1), (-1, 0), (1, 0)]


def _side_color(piece: int):
    """Farbe fuer associate/attacker -- der Koenig zaehlt als WEISS."""
    if piece == ATTACKER:
        return BLACK
    if piece in (DEFENDER, KING):
        return WHITE
    return None  # EMPTY


def _enemy_color(piece: int):
    """Farbe der potentiell geschlagenen Figur -- der Koenig ist KEINE (er wird
    nie kustodial geschlagen, dafuer gibt es die Koenig-Schlagregel separat)."""
    if piece == ATTACKER:
        return BLACK
    if piece == DEFENDER:
        return WHITE
    return None  # EMPTY oder KING


def server_captures(board, to_row: int, to_col: int) -> list[tuple[int, int]]:
    """Geschlagene Felder nach einem Zug auf (to_row, to_col) -- Server-Logik."""
    mover = board.get(to_row, to_col)
    attacker = _side_color(mover)
    if attacker is None:
        return []

    king_pos = board.find_king()
    expected_enemy = BLACK if attacker == WHITE else WHITE

    caps: set[tuple[int, int]] = set()
    for dr, dc in _ALIGN:
        a_row, a_col = to_row + 2 * dr, to_col + 2 * dc  # associate
        if not board.in_bounds(a_row, a_col):
            continue
        e_row, e_col = to_row + dr, to_col + dc  # enemy (eingeklemmt)

        assoc_color = _side_color(board.get(a_row, a_col))
        enemy_color = _enemy_color(board.get(e_row, e_col))
        on_throne = (a_row, a_col) == THRONE
        on_corner = (a_row, a_col) in CORNERS

        # (1) normale kustodiale Klemme durch eigene Figur
        if assoc_color == attacker and enemy_color == expected_enemy:
            caps.add((e_row, e_col))
        # (2) leerer Thron als Klemm-Wand
        if king_pos != THRONE and on_throne and enemy_color == expected_enemy:
            caps.add((e_row, e_col))
        # (3) Thron schlaegt SCHWARZ immer (auch besetzt / Schwarz-am-Zug)
        if on_throne and enemy_color == BLACK:
            caps.add((e_row, e_col))
        # (4) Eckfeld als Klemm-Wand
        if on_corner and enemy_color == expected_enemy:
            caps.add((e_row, e_col))

    return list(caps)


def apply_move_server_faithful(board, move: tuple[int, int, int, int]):
    """Wendet `move` mit Server-treuen Schlagregeln an. Gibt neues Brett zurueck.

    Bewegungsregeln sind bei uns und dem Server identisch -- nur die Schlaege
    weichen ab, deshalb hier dieselbe Figurbewegung wie src.moves.apply_move,
    aber mit server_captures() statt unserer check_captures().
    """
    from_row, from_col, to_row, to_col = move
    piece = board.get(from_row, from_col)

    new_board = board.copy()
    new_board.set(from_row, from_col, EMPTY)
    new_board.set(to_row, to_col, piece)

    if piece == KING and (from_row, from_col) == THRONE:
        new_board.king_left_throne = True

    captures = server_captures(new_board, to_row, to_col)
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
