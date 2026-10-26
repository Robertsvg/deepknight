"""Schlag-Erkennung und Spielende-Logik für Tablut.

Schlagregeln (aus 02 Tablut-Spielregeln.pdf):
- Eine Figur wird geschlagen wenn sie durch den AKTUELLEN Zug orthogonal
  von 2 fremden Figuren eingeklammert wird.
- Eckfeld + leerer Thron zählen als "fremde Figur" beim Klemmen.
- Doppelschlag möglich (16): ein Zug kann 2 Figuren auf einmal schlagen.
- König darf zum Klemmen schwarzer Figuren benutzt werden (17).
- Eine Figur darf SELBST in eine Klemme ziehen ohne geschlagen zu werden (4).

König-Schlagregeln (3 Fälle):
- König auf Thron: braucht 4 Angreifer auf allen Nachbarfeldern.
- König direkt neben Thron: braucht 3 Angreifer (Thron zählt als 4. Seite).
- König irgendwo anders: wie normale Figur (2 Angreifer reichen).
"""

from src.board import ATTACKER, BLACK, CORNERS, DEFENDER, EMPTY, KING, THRONE, WHITE

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def is_hostile_for(board, row, col, side):
    """Ist (row, col) eine 'feindliche Mauer' für eine Figur der Seite `side`?

    Eine Figur der Seite `side` wird geschlagen wenn sie zwischen 2 hostilen
    Feldern liegt. Hostile Felder sind:
    - Gegnerische Figuren
    - Eckfelder (immer)
    - Leerer Thron (immer)
    """
    if not board.in_bounds(row, col):
        return False
    if (row, col) in CORNERS:
        return True
    if (row, col) == THRONE and board.is_empty(row, col):
        return True
    piece = board.get(row, col)
    if piece == EMPTY:
        return False
    if side == BLACK:
        return piece in (DEFENDER, KING)
    else:
        return piece == ATTACKER


def check_captures(board, moved_to):
    """Prüfe nach einem Zug nach `moved_to` welche gegnerischen Figuren geschlagen wurden.

    Returns: Liste der geschlagenen Positionen [(row, col), ...].

    Sandwich-Logik: in jede der 4 Richtungen vom Zielfeld:
    - Schritt 1: Steht dort eine gegnerische Figur (kein König)?
    - Schritt 2: Steht dahinter eine "feindliche Wand" für diese Figur?
      (= eigene Figur, Eckfeld, oder leerer Thron)
    - Wenn beides ja: Figur geschlagen, in captures aufnehmen.

    Doppelschlag wird automatisch erkannt, weil wir alle 4 Richtungen prüfen.
    König wird hier ignoriert - dafür ist is_king_captured() zuständig.
    """
    captures = []
    moved_row, moved_col = moved_to
    moving_piece = board.get(moved_row, moved_col)

    if moving_piece == EMPTY:
        return captures

    if moving_piece == ATTACKER:
        moving_side = BLACK
    else:
        moving_side = WHITE

    for dr, dc in DIRECTIONS:
        n_row, n_col = moved_row + dr, moved_col + dc
        if not board.in_bounds(n_row, n_col):
            continue

        neighbor = board.get(n_row, n_col)
        if neighbor == EMPTY:
            continue

        if moving_side == BLACK:
            if neighbor != DEFENDER:
                continue
        else:
            if neighbor != ATTACKER:
                continue

        opponent_side = WHITE if moving_side == BLACK else BLACK
        b_row, b_col = n_row + dr, n_col + dc
        if is_hostile_for(board, b_row, b_col, opponent_side):
            captures.append((n_row, n_col))

    return captures


def is_king_captured(board):
    """Ist der König auf dem Brett geschlagen?

    3 Fälle:
    - König auf Thron: alle 4 Nachbarfelder mit Angreifern besetzt.
    - König direkt neben Thron: 3 anderen Nachbarn mit Angreifern
      (der Thron selbst zählt als 4. Wand).
    - König sonst: 2 Angreifer orthogonal eingeklammert
      (wie normale Figur, mit Eckfeld als Klammer-Hilfe).
    """
    king_pos = board.find_king()
    if king_pos is None:
        return True

    k_row, k_col = king_pos
    on_throne = king_pos == THRONE
    next_to_throne = (k_row, k_col) in [
        (THRONE[0] - 1, THRONE[1]),
        (THRONE[0] + 1, THRONE[1]),
        (THRONE[0], THRONE[1] - 1),
        (THRONE[0], THRONE[1] + 1),
    ]

    if on_throne or next_to_throne:
        for dr, dc in DIRECTIONS:
            n_row, n_col = k_row + dr, k_col + dc
            if not board.in_bounds(n_row, n_col):
                return False
            if (n_row, n_col) == THRONE:
                continue
            if not board.is_attacker(n_row, n_col):
                return False
        return True

    pairs = [
        ((-1, 0), (1, 0)),
        ((0, -1), (0, 1)),
    ]
    for (dr1, dc1), (dr2, dc2) in pairs:
        r1, c1 = k_row + dr1, k_col + dc1
        r2, c2 = k_row + dr2, k_col + dc2
        if is_hostile_for(board, r1, c1, WHITE) and is_hostile_for(
            board, r2, c2, WHITE
        ):
            return True
    return False


def is_game_over(board, history=None, check_no_moves=False):
    """Returns: 'white_wins', 'black_wins', 'draw' oder None."""

    king_pos = board.find_king()

    if king_pos is None:
        return "black_wins"

    if king_pos in CORNERS:
        return "white_wins"

    if is_king_captured(board):
        return "black_wins"

    if board.halfmoves_no_capture >= 50:
        return "draw"

    # Stellungswiederholung
    if history:
        from src.fen import to_fen

        current_fen = to_fen(board)

        if history.count(current_fen) >= 3:
            return "draw"

    # Zugzwang
    if check_no_moves:
        from src.moves import generate_legal_moves

        moves = list(generate_legal_moves(board, board.side_to_move))

        if not moves:
            return "draw"

    return None
