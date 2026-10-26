"""Tests fuer die Transposition Table.

Wichtigster Test: Alpha-Beta mit TT liefert das GLEICHE Ergebnis wie
Alpha-Beta ohne TT -- aber mit weniger untersuchten Knoten. Wenn das
nicht stimmt, ist das Flag-Handling kaputt.
"""

from src.alpha_beta import alpha_beta, alpha_beta_with_count
from src.alpha_beta_tt import alpha_beta_tt, alpha_beta_tt_with_count
from src.evaluation import WIN_SCORE
from src.fen import STARTING_FEN, parse_fen
from src.transposition_table import (
    EXACT,
    LOWER_BOUND,
    UPPER_BOUND,
    TranspositionTable,
)

# --- TTEntry / TranspositionTable Grundverhalten -------------------------


def test_empty_table_returns_none():
    tt = TranspositionTable()
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    assert tt.lookup(board) is None
    assert tt.misses == 1
    assert tt.hits == 0


def test_store_then_lookup():
    tt = TranspositionTable()
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt.store(board, depth=3, score=42.0, flag=EXACT, best_move=(7, 1, 7, 0))

    entry = tt.lookup(board)
    assert entry is not None
    assert entry.depth == 3
    assert entry.score == 42.0
    assert entry.flag == EXACT
    assert entry.best_move == (7, 1, 7, 0)
    assert tt.hits == 1


def test_deeper_search_overwrites_shallower():
    tt = TranspositionTable()
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt.store(board, depth=2, score=10.0, flag=EXACT, best_move=None)
    tt.store(board, depth=4, score=99.0, flag=EXACT, best_move=None)

    entry = tt.lookup(board)
    assert entry.depth == 4
    assert entry.score == 99.0


def test_shallower_search_does_not_overwrite_deeper():
    tt = TranspositionTable()
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt.store(board, depth=5, score=99.0, flag=EXACT, best_move=None)
    tt.store(board, depth=2, score=10.0, flag=EXACT, best_move=None)

    entry = tt.lookup(board)
    assert entry.depth == 5
    assert entry.score == 99.0


def test_clear_empties_table_and_counters():
    tt = TranspositionTable()
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt.store(board, depth=1, score=0.0, flag=EXACT, best_move=None)
    tt.lookup(board)

    tt.clear()
    assert len(tt) == 0
    assert tt.hits == 0
    assert tt.misses == 0
    assert tt.stores == 0


def test_two_different_boards_get_separate_entries():
    """Board ist hashbar -> zwei verschiedene Stellungen kollidieren nicht."""
    tt = TranspositionTable()
    b1 = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    b2 = parse_fen("9/9/9/9/9/9/9/rK1r5/9 s 0 1")

    tt.store(b1, depth=2, score=10.0, flag=EXACT, best_move=None)
    tt.store(b2, depth=2, score=-10.0, flag=EXACT, best_move=None)

    assert tt.lookup(b1).score == 10.0
    assert tt.lookup(b2).score == -10.0


# --- Alpha-Beta mit TT: Korrektheit --------------------------------------


def test_tt_returns_same_score_as_alpha_beta_simple():
    """Endspiel: TT-AlphaBeta muss exakt denselben Score liefern."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    for depth in [1, 2, 3]:
        s_ab, _ = alpha_beta(board.copy(), depth)
        s_tt, _ = alpha_beta_tt(board.copy(), depth)
        assert s_ab == s_tt, f"Tiefe {depth}: AB={s_ab}, AB+TT={s_tt}"


def test_tt_returns_same_score_as_alpha_beta_startposition():
    """Startstellung: Score muss bei kleiner Tiefe identisch sein."""
    board = parse_fen(STARTING_FEN)
    for depth in [1, 2]:
        s_ab, _ = alpha_beta(board.copy(), depth)
        s_tt, _ = alpha_beta_tt(board.copy(), depth)
        assert s_ab == s_tt, f"Tiefe {depth}: AB={s_ab}, AB+TT={s_tt}"


def test_tt_returns_legal_move():
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    _, move = alpha_beta_tt(board, 2)
    assert move is not None
    assert len(move) == 4


def test_tt_finds_white_wins_in_one():
    """Codex-Stellung 'Weiss gewinnt in 1': Koenig b1 -> a1.

    Korrekter Sieg-Zug muss gefunden werden, Score nahe +WIN_SCORE.
    """
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    score, move = alpha_beta_tt(board, 2)
    assert score >= WIN_SCORE - 1, f"Score sollte ~+WIN_SCORE sein, war {score}"
    assert move == (8, 1, 8, 0)


def test_tt_finds_black_wins_in_one():
    """Codex-Stellung 'Schwarz gewinnt in 1': r-K-r mit Schlagzug."""
    board = parse_fen("9/9/9/9/9/9/9/rK1r5/9 s 0 1")
    score, _ = alpha_beta_tt(board, 2)
    assert score <= -WIN_SCORE + 1, f"Score sollte ~-WIN_SCORE sein, war {score}"


# --- Alpha-Beta mit TT: Effizienz ----------------------------------------


def test_tt_visits_fewer_or_equal_nodes_than_alpha_beta():
    """Mit TT darf die Knotenzahl niemals groesser sein als ohne TT."""
    board = parse_fen(STARTING_FEN)
    for depth in [2, 3]:
        counter_ab = [0]
        alpha_beta_with_count(board.copy(), depth, counter=counter_ab)

        tt = TranspositionTable()
        counter_tt = [0]
        alpha_beta_tt_with_count(
            board.copy(), depth, -WIN_SCORE, WIN_SCORE, tt, counter_tt
        )

        assert counter_tt[0] <= counter_ab[0], (
            f"Tiefe {depth}: AB={counter_ab[0]}, AB+TT={counter_tt[0]}"
        )


def test_tt_actually_records_stores_during_search():
    """Eine reale Suche muss TT-Eintraege ablegen, sonst funktioniert nichts."""
    board = parse_fen(STARTING_FEN)
    tt = TranspositionTable()
    alpha_beta_tt_with_count(board, 2, -WIN_SCORE, WIN_SCORE, tt)
    assert tt.stores > 0, "TT haette Eintraege speichern muessen"
    assert len(tt) > 0


def test_tt_records_hits_when_called_twice():
    """Erst Stellung suchen, dann nochmal -- die zweite Suche muss Treffer haben."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt = TranspositionTable()

    # 1. Suche -- befuellt die TT
    alpha_beta_tt_with_count(board.copy(), 3, -WIN_SCORE, WIN_SCORE, tt)
    stores_after_first = tt.stores
    hits_before = tt.hits

    # 2. Suche derselben Stellung mit derselben (oder geringerer) Tiefe
    # -> die Wurzelstellung muss als Treffer erkannt werden.
    alpha_beta_tt_with_count(board.copy(), 3, -WIN_SCORE, WIN_SCORE, tt)

    assert tt.hits > hits_before, "Zweite Suche haette TT-Hits erzeugen muessen"
    assert stores_after_first > 0


# --- Flag-Handling -------------------------------------------------------


def test_lower_bound_entry_raises_alpha():
    """Wenn ein LOWER_BOUND-Eintrag existiert, sollte alpha angehoben werden.

    Wir testen das indirekt: Wenn wir einen TTEntry mit LOWER_BOUND=score>=beta
    vorm Suchstart einfuegen, muss die Suche sofort einen Cutoff machen.
    """
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt = TranspositionTable()
    # Vor-fuetterung: Score 50 als LOWER_BOUND, Tiefe 3 (>= Anfrage-Tiefe 2)
    tt.store(board, depth=3, score=50.0, flag=LOWER_BOUND, best_move=None)

    # Suche mit beta=40: alpha (was -inf war) wird auf 50 angehoben,
    # alpha>=beta -> Cutoff, Rueckgabe = 50.
    score, _, nodes = alpha_beta_tt_with_count(board, 2, -100.0, 40.0, tt)
    assert score == 50.0
    # Nur die Wurzel wurde besucht -> kein Suchaufwand.
    assert nodes == 1


def test_upper_bound_entry_lowers_beta():
    """UPPER_BOUND-Eintrag soll beta senken koennen -> Cutoff moeglich."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt = TranspositionTable()
    tt.store(board, depth=3, score=-50.0, flag=UPPER_BOUND, best_move=None)

    # alpha=-40, beta=+inf: UPPER_BOUND senkt beta auf -50, alpha>=beta -> Cutoff
    score, _, nodes = alpha_beta_tt_with_count(board, 2, -40.0, 100.0, tt)
    assert score == -50.0
    assert nodes == 1
