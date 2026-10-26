"""SearchState: Killer Moves + History Heuristic fuer M3.

Diese beiden klassischen Zugsortierungs-Heuristiken arbeiten waehrend einer
Suchabfrage zusammen mit der Transposition Table und der taktischen
Move-Ordering. Sie werden in einem SearchState-Objekt gehalten, das durch die
Rekursion gereicht wird -- so muss kein Modul-Globalstate verwendet werden.

KILLER MOVES
------------
Bei jedem Beta-Cutoff merkt man sich pro Suchtiefe die 2 letzten Zuege, die
einen Cutoff verursacht haben (sofern sie KEINE Schlagzuege waren -- Schlaege
sind durch score_move bereits priorisiert). In Geschwisterknoten der
gleichen Tiefe ist die Chance hoch, dass derselbe Zug auch dort gut ist.

HISTORY HEURISTIC
-----------------
Globale Tabelle `history[(from, to)] += depth * depth` fuer alle Zuege, die
einen Cutoff oder eine Verbesserung des best_score ausgeloest haben. Tiefere
Cutoffs zaehlen quadratisch mehr (Standard-Gewichtung). Dient als Tiebreaker
fuer die "stillen" Zuege (kein TT-Hit, kein Schlag, kein Killer).

WARUM KEIN MODUL-STATE?
-----------------------
Pro choose_move()-Aufruf wollen wir saubere Zaehler. Mit Modul-Globals waere
das fehleranfaellig (Tests sehen Reste aus vorherigen Laeufen). Dataclass
plus per-Suche-Instanz haelt den Code testbar und parallelisierbar.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

Move = Tuple[int, int, int, int]


# Maximale Tiefe, fuer die wir Killer Moves vorbereiten.
# Iterative Deepening geht in Tablut praktisch nie ueber 8 in 1s, ein
# grosszuegiger Puffer schadet nicht.
MAX_KILLER_DEPTH = 64
KILLERS_PER_DEPTH = 2


@dataclass
class SearchState:
    """Pro-Suche Zustand fuer Killer- und History-Heuristik.

    Wird von der KI (z.B. AdvancedAI) angelegt und zwischen den
    Iterative-Deepening-Tiefen wiederverwendet (damit fruehe Killer-/History-
    Informationen tiefe Suchen unterstuetzen).
    """

    # killers[depth] = [(move, move) | None Slots], 2 Slots pro Tiefe.
    killers: list = field(
        default_factory=lambda: [[None, None] for _ in range(MAX_KILLER_DEPTH)]
    )
    # history[(from_row, from_col, to_row, to_col)] = int score
    history: dict = field(default_factory=dict)

    def record_killer(self, depth: int, move: Move) -> None:
        """Trage einen Cutoff-Zug als Killer auf dieser Tiefe ein.

        Wenn move schon Slot 0 ist, machen wir nichts (Doppelung vermeiden).
        Sonst shiften wir Slot 0 -> Slot 1 und legen move in Slot 0.
        """
        if depth < 0 or depth >= MAX_KILLER_DEPTH:
            return
        slots = self.killers[depth]
        if slots[0] == move:
            return
        slots[1] = slots[0]
        slots[0] = move

    def is_killer(self, depth: int, move: Move) -> bool:
        if depth < 0 or depth >= MAX_KILLER_DEPTH:
            return False
        return move in self.killers[depth]

    def record_history(self, move: Move, depth: int) -> None:
        """History-Bonus fuer einen erfolgreichen Zug. depth*depth ist Standard."""
        self.history[move] = self.history.get(move, 0) + depth * depth

    def history_score(self, move: Move) -> int:
        return self.history.get(move, 0)

    def reset(self) -> None:
        """Vor neuem choose_move(): killers/history leeren."""
        for slots in self.killers:
            slots[0] = None
            slots[1] = None
        self.history.clear()


# --- Optional bewerteter Move-Sort fuer die Suche ----------------------------
# Diese Funktion ergaenzt order_moves: sie ordnet zusaetzlich nach
# TT-best_move, Killer Moves und History-Score. Sie ueberschreibt order_moves
# NICHT -- bestehende Aufrufe bleiben gueltig.


def ordered_for_search(
    base_ordered: list,
    *,
    tt_move: Optional[Move] = None,
    state: Optional[SearchState] = None,
    depth: int = 0,
) -> list:
    """Sortiere eine bereits durch `order_moves` vorsortierte Liste.

    Reihenfolge:
        1. tt_move (falls vorhanden)
        2. Killer Moves dieser Tiefe (Slot 0 vor Slot 1)
        3. Rest in der von base_ordered gegebenen Reihenfolge,
           innerhalb davon nach History-Score (absteigend, stabil).

    Performance-Hinweis: diese Funktion wird sehr oft aufgerufen. Wir nehmen
    den Schnellpfad wenn weder tt_move noch killers/history etwas Sinnvolles
    beitragen koennen -- dann unveraendert zurueck.
    """
    if not base_ordered:
        return base_ordered

    # Killer-Lookup zusammenstellen (eventuell leer)
    killer0 = killer1 = None
    if state is not None and 0 <= depth < MAX_KILLER_DEPTH:
        slots = state.killers[depth]
        killer0, killer1 = slots[0], slots[1]

    has_history = state is not None and bool(state.history)

    # Schnellpfad: nichts zu tun
    if tt_move is None and killer0 is None and killer1 is None and not has_history:
        return base_ordered

    bucket_tt: list = []
    bucket_killers: list = []
    bucket_rest: list = []

    for move in base_ordered:
        if tt_move is not None and move == tt_move:
            bucket_tt.append(move)
        elif move == killer0 or move == killer1:
            bucket_killers.append(move)
        else:
            bucket_rest.append(move)

    # Killer-Reihenfolge: Slot 0 vor Slot 1 (nur wenn beide vorkommen)
    if killer0 is not None and killer1 is not None and len(bucket_killers) > 1:
        bucket_killers.sort(key=lambda m: 0 if m == killer0 else 1)

    # History nur dann anwenden wenn auch Eintraege existieren.
    if has_history:
        history = state.history
        bucket_rest.sort(key=lambda m: -history.get(m, 0))

    return bucket_tt + bucket_killers + bucket_rest
