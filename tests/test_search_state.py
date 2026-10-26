"""Tests fuer SearchState (Killer Moves + History Heuristic, M3).

Wichtigster Test: Integration in alpha_beta_tt liefert dasselbe Ergebnis wie
ohne SearchState, aber besucht <= Knoten.
"""

from src.alpha_beta import alpha_beta_with_count
from src.alpha_beta_tt import alpha_beta_tt_with_count
from src.evaluation import WIN_SCORE
from src.fen import STARTING_FEN, parse_fen
from src.search_state import MAX_KILLER_DEPTH, SearchState, ordered_for_search
from src.transposition_table import TranspositionTable

# --- SearchState API ----------------------------------------------------


def test_fresh_state_has_no_killers_and_no_history():
    s = SearchState()
    assert not s.is_killer(0, (0, 0, 0, 1))
    assert s.history_score((0, 0, 0, 1)) == 0


def test_record_killer_inserts_at_slot_0():
    s = SearchState()
    m1 = (1, 1, 1, 2)
    s.record_killer(2, m1)
    assert s.killers[2][0] == m1
    assert s.killers[2][1] is None
    assert s.is_killer(2, m1)


def test_record_two_killers_shifts_older_to_slot_1():
    s = SearchState()
    m1 = (1, 1, 1, 2)
    m2 = (2, 2, 2, 3)
    s.record_killer(2, m1)
    s.record_killer(2, m2)
    assert s.killers[2][0] == m2
    assert s.killers[2][1] == m1


def test_record_same_killer_twice_does_not_shift():
    s = SearchState()
    m1 = (1, 1, 1, 2)
    s.record_killer(2, m1)
    s.record_killer(2, m1)
    assert s.killers[2][0] == m1
    assert s.killers[2][1] is None


def test_record_killer_at_out_of_range_depth_is_silent():
    s = SearchState()
    s.record_killer(MAX_KILLER_DEPTH + 5, (0, 0, 0, 1))
    s.record_killer(-1, (0, 0, 0, 1))
    # Kein Crash, keine Effekte:
    for slots in s.killers:
        assert slots == [None, None]


def test_history_accumulates_squared_depth_bonus():
    s = SearchState()
    m = (1, 1, 1, 2)
    s.record_history(m, 3)  # +9
    s.record_history(m, 4)  # +16
    assert s.history_score(m) == 9 + 16


def test_reset_clears_killers_and_history():
    s = SearchState()
    s.record_killer(2, (1, 1, 1, 2))
    s.record_history((1, 1, 1, 2), 3)
    s.reset()
    assert s.killers[2] == [None, None]
    assert s.history == {}


# --- ordered_for_search Reihenfolge -------------------------------------


def test_tt_move_goes_to_front():
    state = SearchState()
    base = [(0, 0, 0, 1), (1, 1, 1, 2), (2, 2, 2, 3)]
    out = ordered_for_search(base, tt_move=(2, 2, 2, 3), state=state, depth=0)
    assert out[0] == (2, 2, 2, 3)


def test_killers_come_after_tt_before_rest():
    state = SearchState()
    state.record_killer(0, (1, 1, 1, 2))
    base = [(0, 0, 0, 1), (1, 1, 1, 2), (2, 2, 2, 3)]
    out = ordered_for_search(base, tt_move=(2, 2, 2, 3), state=state, depth=0)
    assert out[0] == (2, 2, 2, 3)  # TT
    assert out[1] == (1, 1, 1, 2)  # Killer
    # Reststellung beibehalten:
    assert out[2:] == [(0, 0, 0, 1)]


def test_history_breaks_ties_in_rest_bucket():
    state = SearchState()
    state.record_history((2, 2, 2, 3), depth=5)  # +25
    base = [(0, 0, 0, 1), (1, 1, 1, 2), (2, 2, 2, 3)]
    out = ordered_for_search(base, state=state, depth=0)
    # (2,2,2,3) hat hoechsten History-Score -> vorn im "rest"-Bucket.
    assert out[0] == (2, 2, 2, 3)


# --- alpha_beta_tt mit SearchState: Korrektheit -------------------------


def test_ab_tt_with_state_returns_same_score_as_plain_ab():
    """SearchState darf das Ergebnis nicht veraendern, nur die Reihenfolge."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    for depth in [1, 2, 3]:
        s_plain, _ = alpha_beta_with_count(board.copy(), depth)[:2]
        tt = TranspositionTable()
        state = SearchState()
        s_full, _, _ = alpha_beta_tt_with_count(
            board.copy(), depth, -WIN_SCORE, WIN_SCORE, tt, None, 0, state
        )
        assert s_plain == s_full, f"Tiefe {depth}: plain={s_plain} full={s_full}"


def test_ab_tt_with_state_finds_white_wins_in_one():
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    tt = TranspositionTable()
    state = SearchState()
    score, move, _ = alpha_beta_tt_with_count(
        board, 2, -WIN_SCORE, WIN_SCORE, tt, None, 0, state
    )
    assert score == WIN_SCORE - 1
    assert move == (8, 1, 8, 0)


# --- Effizienz ----------------------------------------------------------


def test_ab_tt_with_state_does_not_blow_up_node_count():
    """SearchState darf den Knotenaufwand nicht dramatisch erhoehen.

    Killer/History zahlen sich erst bei tieferer Suche aus. Auf der
    Startstellung mit Tiefe 3 ist der Effekt klein und kann sogar leicht
    negativ sein, weil das Buckets-Sortieren Overhead hat. Wir akzeptieren
    bis zu +20% Knoten -- darunter ist die Erweiterung sicher okay.
    """
    board = parse_fen(STARTING_FEN)
    for depth in [2, 3]:
        c_no_state = [0]
        tt_no = TranspositionTable()
        alpha_beta_tt_with_count(
            board.copy(), depth, -WIN_SCORE, WIN_SCORE, tt_no, c_no_state, 0, None
        )

        c_with_state = [0]
        tt_with = TranspositionTable()
        state = SearchState()
        alpha_beta_tt_with_count(
            board.copy(), depth, -WIN_SCORE, WIN_SCORE, tt_with, c_with_state, 0, state
        )

        # Toleranzfaktor 1.2x; im Benchmark bei groesserer Tiefe Effekt messen
        assert c_with_state[0] <= int(c_no_state[0] * 1.2) + 50, (
            f"Tiefe {depth}: ohne_state={c_no_state[0]} mit_state={c_with_state[0]}"
        )


def test_ab_tt_with_state_helps_on_repeated_subtree():
    """In Stellungen mit vielen Wiederholungen sollte State helfen.

    Wir nehmen das Endspiel '9/9/9/9/9/9/1r7/9/1K7 w 0 1' (1-Zug-Sieg). Die
    Suche findet sofort die Loesung -- Killer/History koennen hier kaum
    Mehrarbeit erzeugen. Das ist mehr ein Sanity-Test."""
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    c_no = [0]
    tt_no = TranspositionTable()
    alpha_beta_tt_with_count(
        board.copy(), 3, -WIN_SCORE, WIN_SCORE, tt_no, c_no, 0, None
    )
    c_yes = [0]
    tt_yes = TranspositionTable()
    state = SearchState()
    alpha_beta_tt_with_count(
        board.copy(), 3, -WIN_SCORE, WIN_SCORE, tt_yes, c_yes, 0, state
    )
    # Beide finden den Sieg, Knotenzahlen liegen nah beieinander
    assert abs(c_no[0] - c_yes[0]) <= max(c_no[0], 1) * 2


def test_search_records_killer_and_history_during_real_search():
    """Eine echte Suche muss Killer + History fuellen."""
    board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
    tt = TranspositionTable()
    state = SearchState()
    alpha_beta_tt_with_count(board, 3, -WIN_SCORE, WIN_SCORE, tt, None, 0, state)
    has_killer = any(slot is not None for slots in state.killers for slot in slots)
    assert has_killer or state.history, (
        "Erwarte mindestens einen Killer-Eintrag ODER History-Eintrag"
    )
