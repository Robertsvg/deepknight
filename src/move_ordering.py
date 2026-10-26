"""
move_ordering.py

Sorts moves before Alpha-Beta.
Good moves should be searched first.
"""

from src.board import ATTACKER, BLACK, CORNERS, KING, WHITE, coords_to_algebraic
from src.moves import apply_move
from src.rules import is_game_over

# Bewertungs-Konstanten fuer score_move (groesser = vielversprechender Zug).
# Reihenfolge der Groessenordnungen bestimmt die Sortier-Prioritaet:
# gewinnender/Koenig-in-Ecke Zug > Schlagzug > Koenig naeher zur Ecke > Angreifer naeher zum Koenig.
SCORE_WINNING_MOVE = 100_000  # Zug beendet das Spiel zu eigenen Gunsten
SCORE_KING_TO_CORNER = 50_000  # Koenig erreicht eine Eck-Fluchtfeld
SCORE_PER_CAPTURE = 1_000  # je geschlagenem gegnerischen Stein
SCORE_KING_CLOSER = 500  # Koenig kommt einer Ecke naeher
SCORE_ATTACKER_TO_KING = 200  # Angreifer kommt dem Koenig naeher


def move_to_string(move: tuple[int, int, int, int]) -> str:
    from_row, from_col, to_row, to_col = move
    return f"{coords_to_algebraic(from_row, from_col)}-{coords_to_algebraic(to_row, to_col)}"


def count_pieces(board) -> tuple[int, int]:
    """Zaehlt (Angreifer, Verteidiger) direkt ueber die Bitboards.

    Nutzt ``int.bit_count()`` (C-Level popcount) statt eines 9x9-Feld-Scans --
    der Aufruf liegt im Move-Ordering-Hot-Path und wird pro Zug mehrfach
    ausgefuehrt. ``defenders`` zaehlt die normalen weissen Steine ohne Koenig
    (konsistent zum vorherigen ``board.get``-Scan, der KING separat behandelte).
    """
    return board.attackers.bit_count(), board.defenders.bit_count()


def distance_to_corner(row: int, col: int) -> int:
    """Manhattan-Distanz zur naechstgelegenen Eckfeld-Ecke."""
    best_distance = 100

    for corner_row, corner_col in CORNERS:
        distance = abs(row - corner_row) + abs(col - corner_col)

        if distance < best_distance:
            best_distance = distance

    return best_distance


def score_move(board, move: tuple[int, int, int, int], depth: int = 0) -> int:
    """Heuristischer Vorab-Score eines Zugs (groesser = vermutlich besser).

    Bewertet ohne Suche: gewinnende Zuege, Schlaege, Koenig-Richtung-Ecke und
    Angreifer-Richtung-Koenig. Dient nur der Zugsortierung, nicht der Suche.
    """

    from_row, from_col, to_row, to_col = move
    piece = board.get(from_row, from_col)
    side = board.side_to_move

    score = 0

    try:
        new_board = apply_move(board, move)
    except ValueError:
        # Illegaler Zug: ans Ende der Sortierung schieben.
        return -999999

    result = is_game_over(new_board)

    # Sofort gewinnender Zug -> hoechste Prioritaet.
    if side == WHITE and result == "white_wins":
        score += SCORE_WINNING_MOVE
    if side == BLACK and result == "black_wins":
        score += SCORE_WINNING_MOVE

    # Schlagzuege: je geschlagenem Gegner ein Bonus.
    old_attackers, old_defenders = count_pieces(board)
    new_attackers, new_defenders = count_pieces(new_board)

    if side == WHITE:
        captured_attackers = old_attackers - new_attackers
        score += captured_attackers * SCORE_PER_CAPTURE
    if side == BLACK:
        captured_defenders = old_defenders - new_defenders
        score += captured_defenders * SCORE_PER_CAPTURE

    # Koenigszuege: Ecke erreichen oder ihr naeher kommen.
    if piece == KING:
        old_distance = distance_to_corner(from_row, from_col)
        new_distance = distance_to_corner(to_row, to_col)

        if (to_row, to_col) in CORNERS:
            score += SCORE_KING_TO_CORNER
        if new_distance < old_distance:
            score += SCORE_KING_CLOSER

    # Angreiferzuege: dem Koenig naeher kommen (Einkreisung).
    if side == BLACK and piece == ATTACKER:
        king_pos = board.find_king()

        if king_pos is not None:
            king_row, king_col = king_pos

            old_distance = abs(from_row - king_row) + abs(from_col - king_col)
            new_distance = abs(to_row - king_row) + abs(to_col - king_col)

            if new_distance < old_distance:
                score += SCORE_ATTACKER_TO_KING

    return score


def order_moves(board, moves, tt_move=None, state=None, depth: int = 0):
    """
    Returns the moves sorted from best-looking to worst-looking.


    Basis-Verhalten (rueckwaertskompatibel): score_move (Schlaege,
    Koenig-Richtung-Ecke). Aufrufe mit nur 2 Argumenten verhalten sich
    exakt wie vorher.

    M3-Erweiterung (optional): wenn `tt_move`, `state` oder beides
    angegeben werden, wird die Liste durch ordered_for_search noch nach
    TT-best_move, Killer Moves und History sortiert -- siehe
    src/search_state.py.
    """
    base = sorted(moves, key=lambda move: score_move(board, move, depth), reverse=True)

    if tt_move is None and state is None:
        return base

    # Lazy import um Modul-Zyklus zu vermeiden.
    from src.search_state import ordered_for_search

    return ordered_for_search(base, tt_move=tt_move, state=state, depth=depth)
