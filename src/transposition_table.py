"""Transposition Table fuer Tablut M3.

Cached bereits bewertete Stellungen, damit Transpositionen (= Stellungen, die
auf verschiedenen Pfaden erreichbar sind) nicht doppelt durchsucht werden.

Wichtig sind die drei Flag-Werte, weil Alpha-Beta nicht immer einen exakten
Score zurueckliefert:
- EXACT       : Score ist der wahre Minimax-Wert (lag im Fenster).
- LOWER_BOUND : ein Beta-Cutoff hat die Suche beendet -> wahrer Wert ist >= score.
- UPPER_BOUND : kein Zug konnte alpha schlagen           -> wahrer Wert ist <= score.

Das Board wird direkt als dict-Key benutzt (board.py definiert __hash__ und
__eq__ auf (attackers, defenders, king, side_to_move, king_left_throne)), daher
brauchen wir kein eigenes Zobrist-Hashing.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

EXACT = 0
LOWER_BOUND = 1
UPPER_BOUND = 2


Move = Optional[Tuple[int, int, int, int]]


@dataclass
class TTEntry:
    """Ein Eintrag in der Transposition Table."""

    depth: int  # Mit welcher Resttiefe wurde dieser Score berechnet?
    score: float  # Berechneter Score (Sicht WEISS)
    flag: int  # EXACT / LOWER_BOUND / UPPER_BOUND
    best_move: Move  # Bester Zug aus dieser Stellung (oder None)


# Obergrenze der gespeicherten Eintraege. Schuetzt vor unbegrenztem
# Speicherwachstum ueber eine lange Turnierpartie. Pro Eintrag ~einige hundert
# Byte -> 1 Mio. Eintraege bleiben deutlich unter typischen Speichergrenzen.
DEFAULT_MAX_SIZE = 1_000_000


class TranspositionTable:
    """Cache von Board-Stellungen mit Suchergebnissen.

    Strategie: bei Kollision (gleiche Stellung schon drin) ueberschreiben wir
    nur, wenn die neue Suche mindestens so tief war wie die alte -- sonst
    verlieren wir verlaessliche, tiefere Informationen.

    Bei Erreichen von ``max_size`` wird die Tabelle geleert, bevor neue
    Eintraege hinzukommen (einfache, deterministische Strategie ohne teure
    LRU-Buchfuehrung -- ausreichend, da die TB pro Zugentscheidung ohnehin
    neu aufgebaut wird).
    """

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE) -> None:
        self.table: dict = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.stores = 0

    def lookup(self, board) -> Optional[TTEntry]:
        """Hole TT-Eintrag fuer diese Stellung (oder None). Zaehlt hits/misses."""
        entry = self.table.get(board)
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        return entry

    def store(
        self, board, depth: int, score: float, flag: int, best_move: Move
    ) -> None:
        """Speichere Eintrag. Ueberschreibt nur bei mind. gleicher Suchtiefe."""
        existing = self.table.get(board)
        if existing is None or depth >= existing.depth:
            # Groessenlimit: vor einem NEUEN Schluessel ggf. leeren.
            if existing is None and len(self.table) >= self.max_size:
                self.table.clear()
            self.table[board] = TTEntry(depth, score, flag, best_move)
            self.stores += 1

    def clear(self) -> None:
        """Leere die Tabelle. Zaehler werden zurueckgesetzt."""
        self.table.clear()
        self.hits = 0
        self.misses = 0
        self.stores = 0

    def __len__(self) -> int:
        return len(self.table)
