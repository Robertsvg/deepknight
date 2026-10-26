"""
Board.py

This file stores the Tablut board using bitboards.

The board has 9x9 fields.
Each field gets one bit:
index = row * 9 + col

There are three bitboards:
- attackers: black stones
- defenders: white stones without the king
- king: the king
"""

EMPTY = "."
ATTACKER = "r"
DEFENDER = "R"
KING = "K"

WHITE = "w"
BLACK = "s"

BOARD_SIZE = 9
THRONE = (4, 4)
CORNERS = [(0, 0), (0, 8), (8, 0), (8, 8)]


def _bit(row: int, col: int) -> int:
    return 1 << (row * BOARD_SIZE + col)


THRONE_BIT = _bit(4, 4)

CORNERS_BB = 0
for row, col in CORNERS:
    CORNERS_BB |= _bit(row, col)


EDGE_BB = 0
for i in range(BOARD_SIZE):
    EDGE_BB |= _bit(0, i)
    EDGE_BB |= _bit(8, i)
    EDGE_BB |= _bit(i, 0)
    EDGE_BB |= _bit(i, 8)


_THRONE_NEIGHBORS_BB = _bit(3, 4) | _bit(5, 4) | _bit(4, 3) | _bit(4, 5)

_ROW_MASK = []
_COL_MASK = []

for row in range(BOARD_SIZE):
    mask = 0
    for col in range(BOARD_SIZE):
        mask |= _bit(row, col)
    _ROW_MASK.append(mask)

for col in range(BOARD_SIZE):
    mask = 0
    for row in range(BOARD_SIZE):
        mask |= _bit(row, col)
    _COL_MASK.append(mask)


class Board:
    """
    Board state for Tablut.

    attackers: black stones
    defenders: normal white stones
    king: the king position
    """

    __slots__ = (
        "attackers",
        "defenders",
        "king",
        "side_to_move",
        "king_left_throne",
        "halfmoves_no_capture",
        "fullmove_number",
    )

    def __init__(self) -> None:
        self.attackers = 0
        self.defenders = 0
        self.king = 0

        self.side_to_move = BLACK
        self.king_left_throne = False
        self.halfmoves_no_capture = 0
        self.fullmove_number = 1

    @staticmethod
    def _bit(row: int, col: int) -> int:
        return 1 << (row * BOARD_SIZE + col)

    @staticmethod
    def in_bounds(row: int, col: int) -> bool:
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    @property
    def occupied(self) -> int:
        return self.attackers | self.defenders | self.king

    @property
    def white_bb(self) -> int:
        return self.defenders | self.king

    def get(self, row: int, col: int) -> str:
        b = self._bit(row, col)

        if self.king & b:
            return KING
        if self.defenders & b:
            return DEFENDER
        if self.attackers & b:
            return ATTACKER

        return EMPTY

    def set(self, row: int, col: int, value: str) -> None:
        if not self.in_bounds(row, col):
            raise ValueError(f"Field is outside the board: {(row, col)}")

        if value not in (EMPTY, ATTACKER, DEFENDER, KING):
            raise ValueError(f"Invalid piece: {value}")

        b = self._bit(row, col)

        # First remove whatever is already on this square
        self.attackers &= ~b
        self.defenders &= ~b
        self.king &= ~b

        # Then put the new piece there
        if value == ATTACKER:
            self.attackers |= b
        elif value == DEFENDER:
            self.defenders |= b
        elif value == KING:
            self.king = b

    def is_empty(self, row: int, col: int) -> bool:
        return not (self.occupied & self._bit(row, col))

    def is_corner(self, row: int, col: int) -> bool:
        return bool(CORNERS_BB & self._bit(row, col))

    def is_throne(self, row: int, col: int) -> bool:
        return (row, col) == THRONE

    def is_attacker(self, row: int, col: int) -> bool:
        return bool(self.attackers & self._bit(row, col))

    def is_defender(self, row: int, col: int) -> bool:
        return bool(self.white_bb & self._bit(row, col))

    def is_king(self, row: int, col: int) -> bool:
        return bool(self.king & self._bit(row, col))

    def find_king(self) -> tuple[int, int] | None:
        if self.king == 0:
            return None

        index = self.king.bit_length() - 1
        row = index // BOARD_SIZE
        col = index % BOARD_SIZE

        return row, col

    def king_on_edge(self) -> bool:
        return bool(self.king & EDGE_BB)

    def king_on_throne(self) -> bool:
        return bool(self.king & THRONE_BIT)

    def king_beside_throne(self) -> bool:
        return bool(self.king & _THRONE_NEIGHBORS_BB)

    def empty_bb(self) -> int:
        all_fields = (1 << 81) - 1
        return all_fields & ~self.occupied

    def copy(self) -> "Board":
        new_board = Board()

        new_board.attackers = self.attackers
        new_board.defenders = self.defenders
        new_board.king = self.king

        new_board.side_to_move = self.side_to_move
        new_board.king_left_throne = self.king_left_throne
        new_board.halfmoves_no_capture = self.halfmoves_no_capture
        new_board.fullmove_number = self.fullmove_number

        return new_board

    def __str__(self) -> str:
        lines = []

        for row in range(BOARD_SIZE):
            rank = 9 - row
            fields = []

            for col in range(BOARD_SIZE):
                fields.append(self.get(row, col))

            lines.append(f"{rank} " + " ".join(fields))

        lines.append("  a b c d e f g h i")

        if self.side_to_move == WHITE:
            lines.append("To move: White")
        else:
            lines.append("To move: Black")

        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented

        return (
            self.attackers == other.attackers
            and self.defenders == other.defenders
            and self.king == other.king
            and self.side_to_move == other.side_to_move
            and self.king_left_throne == other.king_left_throne
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.attackers,
                self.defenders,
                self.king,
                self.side_to_move,
                self.king_left_throne,
            )
        )


def algebraic_to_coords(notation: str) -> tuple[int, int]:
    """
    Converts chess-like notation to board coordinates.

    Example:
    b2 -> (7, 1)
    """
    col = ord(notation[0].lower()) - ord("a")
    row = 9 - int(notation[1])

    return row, col


def coords_to_algebraic(row: int, col: int) -> str:
    """
    Converts board coordinates to chess-like notation.

    Example:
    (7, 1) -> b2
    """
    letter = chr(ord("a") + col)
    number = 9 - row

    return f"{letter}{number}"


def setup_initial_position(board: Board) -> None:
    """
    Sets the normal starting position for Tablut.
    Black starts.
    """

    board.attackers = 0
    board.defenders = 0
    board.king = 0

    board.side_to_move = BLACK
    board.king_left_throne = False
    board.halfmoves_no_capture = 0
    board.fullmove_number = 1

    attackers = [
        (0, 3),
        (0, 4),
        (0, 5),
        (8, 3),
        (8, 4),
        (8, 5),
        (3, 0),
        (4, 0),
        (5, 0),
        (3, 8),
        (4, 8),
        (5, 8),
        (1, 4),
        (7, 4),
        (4, 1),
        (4, 7),
    ]

    defenders = [
        (3, 4),
        (5, 4),
        (4, 3),
        (4, 5),
        (2, 4),
        (6, 4),
        (4, 2),
        (4, 6),
    ]

    for row, col in attackers:
        board.set(row, col, ATTACKER)

    for row, col in defenders:
        board.set(row, col, DEFENDER)

    board.set(4, 4, KING)

    board.side_to_move = BLACK
