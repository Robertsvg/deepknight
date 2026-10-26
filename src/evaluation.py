"""Board evaluation for Tablut.

Scores are from White's perspective:
- positive values are good for White
- negative values are good for Black
"""

from src.board import (
    BOARD_SIZE,
    CORNERS,
    THRONE,
    THRONE_BIT,
    _bit,
)
from src.rules import is_game_over

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
WIN_SCORE = 10000.0
DRAW_SCORE = 0.0
DEFENDER_VALUE = 1.0
ATTACKER_VALUE = 1.0
KING_DISTANCE_WEIGHT = 3.0
KING_MOBILITY_WEIGHT = 0.3
KING_DANGER_WEIGHT = 3.0
KING_THREAT_WEIGHT = 8.0
ESCAPE_LANE_WEIGHT = 4.5
CORNER_APPROACH_WEIGHT = 1.8
DEFENDER_SHIELD_WEIGHT = 0.35
# Corner-Safety: Ecken-Anziehung (king_distance + corner_approach) wird pro
# Ecke mit der Zahl der Angreifer in Eck-Naehe (Manhattan <= 4) herunterskaliert.
# Contest-Erkenntnis (11.07.): Der Koenig lief frueh in die linke Angreifer-
# Kaserne und wurde bei (2,0) eingeklemmt -- eine bewachte Ecke darf nicht
# genauso anziehen wie eine freie.
CORNER_REGION_DISTANCE = 4
CORNER_SAFETY_PENALTY = 0.35
CORNER_SAFETY_MIN = 0.2
# MAX_KING_CORNER_DISTANCE: used to convert distance to closeness score.
# Set to 16 (max possible Manhattan distance on a 9x9 board) so that even
# the center (dist=8) produces a positive closeness of 8.
MAX_KING_CORNER_DISTANCE = 16
OPENING_MIN_PIECES = 20
ENDGAME_MAX_PIECES = 8
ENDGAME_CORNER_DISTANCE = 2


# Precomputed bitboards for fast adjacency checks around the king.
# _ADJACENT_BB[bit_idx] = bitboard of the 4 orthogonal neighbors of that square.
# _NEAR_BB[bit_idx]     = bitboard of the 4 squares 2 steps away (used for "danger").
_ADJACENT_BB = [0] * (BOARD_SIZE * BOARD_SIZE)
_NEAR_BB = [0] * (BOARD_SIZE * BOARD_SIZE)
for _r in range(BOARD_SIZE):
    for _c in range(BOARD_SIZE):
        _idx = _r * BOARD_SIZE + _c
        _adj = 0
        _near = 0
        for _dr, _dc in DIRECTIONS:
            _ar, _ac = _r + _dr, _c + _dc
            if 0 <= _ar < BOARD_SIZE and 0 <= _ac < BOARD_SIZE:
                _adj |= _bit(_ar, _ac)
            _nr, _nc = _r + 2 * _dr, _c + 2 * _dc
            if 0 <= _nr < BOARD_SIZE and 0 <= _nc < BOARD_SIZE:
                _near |= _bit(_nr, _nc)
        _ADJACENT_BB[_idx] = _adj
        _NEAR_BB[_idx] = _near

# _CORNER_REGION_BB[corner] = Felder mit Manhattan-Distanz <= CORNER_REGION_DISTANCE
# zur Ecke (ohne die Ecke selbst) -- fuer die Corner-Safety-Skalierung.
_CORNER_REGION_BB = {}
for _corner in CORNERS:
    _mask = 0
    for _r in range(BOARD_SIZE):
        for _c in range(BOARD_SIZE):
            _d = abs(_r - _corner[0]) + abs(_c - _corner[1])
            if 0 < _d <= CORNER_REGION_DISTANCE:
                _mask |= _bit(_r, _c)
    _CORNER_REGION_BB[_corner] = _mask


def evaluate(board) -> float:
    """Return a White-perspective score for `board` (depth-independent)."""
    result = is_game_over(board)
    if result == "white_wins":
        return WIN_SCORE
    if result == "black_wins":
        return -WIN_SCORE
    if result == "draw":
        return DRAW_SCORE

    return (
        material_score(board)
        + king_distance_score(board)
        + king_mobility_score(board)
        + escape_lane_score(board)
        + king_danger_score(board)
        + corner_approach_score(board)
        + defender_shield_score(board)
    )


def terminal_score(board, plies_from_root: int) -> float:
    """Return a depth-adjusted terminal score (or None if not terminal).

    Schnelle Siege muessen hoeher bewertet werden als
    spaete. Diese Funktion zieht von WIN_SCORE eine kleine Strafe ab, die mit der
    Anzahl der Halbzuege bis zur Wurzel waechst -- so bevorzugt die Suche kuerzere
    Mattfuehrungen. `plies_from_root` ist die Anzahl der Halbzuege, die die Suche
    schon hinter sich hat bevor sie diese Stellung erreicht.

    Returns:
        - depth-adjusted Score wenn die Stellung terminal ist, sonst None.
    """
    result = is_game_over(board)
    if result is None:
        return None
    if result == "white_wins":
        return WIN_SCORE - plies_from_root
    if result == "black_wins":
        return -WIN_SCORE + plies_from_root
    return DRAW_SCORE


def material_score(board) -> float:
    """Reward White defenders and penalize Black attackers.

    Attackers start 16 vs 8 defenders, so we reduce ATTACKER_VALUE to prevent
    the material term from overwhelming all positional incentives for White.
    """
    defenders = board.defenders.bit_count()
    attackers = board.attackers.bit_count()

    return defenders * DEFENDER_VALUE - attackers * ATTACKER_VALUE


def _corner_safety(board, corner) -> float:
    """Skalierungsfaktor [CORNER_SAFETY_MIN, 1.0] fuer die Anziehung einer Ecke.

    Je mehr Angreifer in der Eck-Region stehen, desto weniger darf die Ecke
    den Koenig anziehen -- ein Lauf in eine bewachte Ecke ist eine Falle,
    keine Fluchtchance.
    """
    n = (board.attackers & _CORNER_REGION_BB[corner]).bit_count()
    return max(CORNER_SAFETY_MIN, 1.0 - CORNER_SAFETY_PENALTY * n)


def king_distance_score(board) -> float:
    """Reward king positions closer to a SAFE escape corner.

    Uses MAX_KING_CORNER_DISTANCE=16 (max possible Manhattan distance on 9x9)
    so the center (distance=8) produces closeness=8 rather than 0, giving the
    king a meaningful gradient to follow towards the corners from the very start.
    Each corner's pull is scaled by _corner_safety() so guarded corners
    attract less; the king follows the best (closeness x safety) corner.
    """
    king_pos = board.find_king()
    if king_pos is None:
        return -WIN_SCORE

    best = max(
        (
            MAX_KING_CORNER_DISTANCE
            - abs(king_pos[0] - corner[0])
            - abs(king_pos[1] - corner[1])
        )
        * _corner_safety(board, corner)
        for corner in CORNERS
    )

    return best * KING_DISTANCE_WEIGHT


def game_phase(board) -> str:
    """Classify the board as opening, midgame, or endgame."""
    king_pos = board.find_king()
    if king_pos is None:
        return "endgame"

    total_pieces = board.attackers.bit_count() + board.defenders.bit_count() + 1
    if king_pos == THRONE and total_pieces >= OPENING_MIN_PIECES:
        return "opening"

    if (
        total_pieces <= ENDGAME_MAX_PIECES
        or board.king_on_edge()
        or _king_corner_distance(king_pos) <= ENDGAME_CORNER_DISTANCE
    ):
        return "endgame"

    return "midgame"


def king_mobility_score(board) -> float:
    """Reward the number of legal king moves available to White.

    Die urspruengliche Version rief
    `generate_legal_moves(board, WHITE)` auf -- das generiert ALLE Zuege aller
    Defenders und filtert dann raus. Hier zaehlen wir die Koenigszuege direkt
    auf den Bitboards: vom Koenig aus 4 Richtungen weit gehen bis erste blockierte
    Stelle. Faktor ~50-100x schneller, gleiche Semantik (Koenig darf nicht auf
    Thron, nicht auf besetzte Felder).
    """
    king_pos = board.find_king()
    if king_pos is None:
        return -WIN_SCORE

    occupied = board.occupied
    king_row, king_col = king_pos
    moves = 0

    for dr, dc in DIRECTIONS:
        r, c = king_row + dr, king_col + dc
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
            target_bit = _bit(r, c)
            if occupied & target_bit:
                break
            # Koenig darf nicht zurueck auf den Thron
            if target_bit == THRONE_BIT:
                r += dr
                c += dc
                continue
            moves += 1
            r += dr
            c += dc

    return moves * KING_MOBILITY_WEIGHT


def escape_lane_score(board) -> float:
    """Reward clear straight paths from the king to an escape corner."""
    king_pos = board.find_king()
    if king_pos is None:
        return -WIN_SCORE

    clear_lanes = sum(
        1
        for corner in CORNERS
        if _same_line(king_pos, corner)
        and _path_to_corner_is_clear(board, king_pos, corner)
    )
    return clear_lanes * ESCAPE_LANE_WEIGHT


def king_danger_score(board) -> float:
    """Penalize attackers close to the king and immediate clamp threats.

    Performance-Refactor: statt 8 separater in_bounds/is_attacker-Aufrufe nutzen
    wir vorgerechnete _ADJACENT_BB / _NEAR_BB Masken und zaehlen die Treffer
    mit `bit_count()` (popcount). Geht in CPython direkt auf C-Ebene.

    Klemm-Bedrohung (Contest-Erkenntnis 11.07.): Der Koenig wurde bei (2,0)
    geschlagen, weil ein Angreifer von (1,1) nach (1,0) ziehen konnte --
    diagonal stehende Angreifer waren fuer die reine Nachbarschafts-Zaehlung
    unsichtbar. Deshalb: Steht gegenueber vom Koenig bereits eine Klemm-Wand
    (Angreifer oder Eckfeld) und kann irgendein Angreifer das leere Feld auf
    der anderen Seite in EINEM Zug erreichen, ist das eine akute Schlagdrohung.
    """
    king_pos = board.find_king()
    if king_pos is None:
        return -WIN_SCORE

    king_row, king_col = king_pos
    idx = king_row * BOARD_SIZE + king_col

    adjacent_attackers = (board.attackers & _ADJACENT_BB[idx]).bit_count()
    nearby_attackers = (board.attackers & _NEAR_BB[idx]).bit_count()

    danger = adjacent_attackers + 0.5 * nearby_attackers

    # Akute Klemm-Bedrohungen (nur abseits des Throns: dort gilt die
    # 2-Angreifer-Klemme, vgl. rules.is_king_captured).
    threats = 0
    on_or_next_to_throne = abs(king_row - THRONE[0]) + abs(king_col - THRONE[1]) <= 1
    if not on_or_next_to_throne:
        occupied = board.occupied
        for dr, dc in DIRECTIONS:
            s_row, s_col = king_row + dr, king_col + dc
            o_row, o_col = king_row - dr, king_col - dc
            if not (0 <= s_row < BOARD_SIZE and 0 <= s_col < BOARD_SIZE):
                continue
            if occupied & _bit(s_row, s_col):
                continue  # Klemmfeld muss leer sein
            if (s_row, s_col) in CORNERS:
                continue  # Angreifer duerfen nicht auf Eckfeldern landen
            # Wand gegenueber: Angreifer oder Eckfeld (Brettrand zaehlt nicht)
            if not (0 <= o_row < BOARD_SIZE and 0 <= o_col < BOARD_SIZE):
                continue
            if not (board.attackers & _bit(o_row, o_col) or (o_row, o_col) in CORNERS):
                continue
            # Erreicht irgendein Angreifer das Klemmfeld in einem Zug?
            if _attacker_can_reach(board, s_row, s_col):
                threats += 1

    return -(danger * KING_DANGER_WEIGHT + threats * KING_THREAT_WEIGHT)


def _attacker_can_reach(board, row: int, col: int) -> bool:
    """Kann ein Angreifer das (leere) Feld (row, col) in einem Zug erreichen?"""
    occupied = board.occupied
    for dr, dc in DIRECTIONS:
        r, c = row + dr, col + dc
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
            square = _bit(r, c)
            if occupied & square:
                if board.attackers & square:
                    return True
                break
            r += dr
            c += dc
    return False


def corner_approach_score(board) -> float:
    """Reward the king for having clear steps toward a corner.

    For each corner, we check how many unobstructed orthogonal steps the king
    can take in the direction of that corner (i.e. how far it can slide toward
    the corner's row OR column before hitting a blocker).  The more clear steps
    toward ANY corner, the higher the score.  Unlike escape_lane_score, the path
    to the corner itself does not need to be fully clear; we just reward progress.

    This avoids rewarding king positions that are on the corner row/col but
    surrounded by attackers (e.g. king rushing to row 0 center where Black
    attackers are clustered).
    """
    king_pos = board.find_king()
    if king_pos is None:
        return -WIN_SCORE

    king_row, king_col = king_pos
    occupied = board.occupied
    best = 0.0

    for corner in CORNERS:
        c_row, c_col = corner
        dist = abs(king_row - c_row) + abs(king_col - c_col)
        if dist == 0:
            # Already at the corner — handled by win detection
            continue

        # How many clear steps can the king take in the row-direction toward corner?
        # (only counts if not already on that row)
        row_steps = 0
        if king_row != c_row:
            dr = 1 if c_row > king_row else -1
            r = king_row + dr
            while r != c_row and r in range(BOARD_SIZE):
                if occupied & _bit(r, king_col):
                    break
                row_steps += 1
                r += dr

        # How many clear steps can the king take in the col-direction toward corner?
        col_steps = 0
        if king_col != c_col:
            dc = 1 if c_col > king_col else -1
            c = king_col + dc
            while c != c_col and c in range(BOARD_SIZE):
                if occupied & _bit(king_row, c):
                    break
                col_steps += 1
                c += dc

        # Credit = max steps toward this corner in either direction
        # Normalize by max distance to give 0..1 range, then scale by closeness
        max_possible = max(abs(king_row - c_row), abs(king_col - c_col), 1)
        progress = max(row_steps, col_steps) / max_possible
        # Also give bonus for total closeness to this corner
        closeness_bonus = (MAX_KING_CORNER_DISTANCE - dist) / MAX_KING_CORNER_DISTANCE
        # Bewachte Ecken ziehen weniger an (siehe _corner_safety)
        score = progress * closeness_bonus * 10.0 * _corner_safety(board, corner)
        best = max(best, score)

    return best * CORNER_APPROACH_WEIGHT


def defender_shield_score(board) -> float:
    """Reward defenders positioned to shield the king's escape route.

    Defenders adjacent to the king protect it from capture (the king needs
    fewer surrounding attackers to be dangerous when defenders are nearby).
    But defenders blocking the king's escape are bad; this term does NOT
    check directionality — it is a simple proximity bonus to encourage the
    formation of a protective escort.
    """
    king_pos = board.find_king()
    if king_pos is None:
        return -WIN_SCORE

    king_row, king_col = king_pos
    idx = king_row * BOARD_SIZE + king_col

    # Defenders adjacent to king
    adjacent_defenders = (board.defenders & _ADJACENT_BB[idx]).bit_count()

    return adjacent_defenders * DEFENDER_SHIELD_WEIGHT


def _king_corner_distance(king_pos) -> int:
    row, col = king_pos
    return min(abs(row - corner[0]) + abs(col - corner[1]) for corner in CORNERS)


def _same_line(start, end) -> bool:
    return start[0] == end[0] or start[1] == end[1]


def _path_to_corner_is_clear(board, king_pos, corner) -> bool:
    king_row, king_col = king_pos
    corner_row, corner_col = corner
    row_step = _step(corner_row - king_row)
    col_step = _step(corner_col - king_col)

    row = king_row + row_step
    col = king_col + col_step
    while (row, col) != corner:
        if not board.is_empty(row, col):
            return False
        row += row_step
        col += col_step

    return board.is_empty(corner_row, corner_col)


def _step(delta: int) -> int:
    if delta == 0:
        return 0
    return delta // abs(delta)
