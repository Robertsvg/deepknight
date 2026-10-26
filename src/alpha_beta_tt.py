"""Alpha-Beta-Suche mit Transposition Table (M3).

Erweitert src/alpha_beta.py um:
1. TT-Lookup vor der Suche -- erkannte Stellungen liefern sofort einen Score
   (mit korrekter Behandlung von EXACT / LOWER_BOUND / UPPER_BOUND).
2. TT-best_move wird zuerst probiert (Move-Ordering-Synergie).
3. Optional: Killer Moves + History Heuristic via SearchState -- siehe
   src/search_state.py.
4. TT-Store nach der Suche mit dem richtigen Flag.

Das initiale AB-Fenster ist
[-WIN_SCORE, +WIN_SCORE] statt [-inf, +inf] sein. Das setzen wir hier als
Default, damit mehr Cutoffs moeglich sind, wenn ein Sieg sicher ist.
"""

from src.board import WHITE
from src.evaluation import WIN_SCORE, evaluate, terminal_score
from src.move_ordering import order_moves
from src.moves import apply_move, generate_legal_moves
from src.transposition_table import (
    EXACT,
    LOWER_BOUND,
    UPPER_BOUND,
    TranspositionTable,
)


def alpha_beta_tt(
    board,
    depth,
    alpha=-WIN_SCORE,
    beta=WIN_SCORE,
    tt=None,
    counter=None,
    state=None,
):
    """Alpha-Beta mit Transposition Table. Returns (score, best_move)."""
    score, move, _ = alpha_beta_tt_with_count(
        board, depth, alpha, beta, tt, counter, state=state
    )
    return score, move


def alpha_beta_tt_with_count(
    board,
    depth,
    alpha=-WIN_SCORE,
    beta=WIN_SCORE,
    tt=None,
    counter=None,
    plies_from_root=0,
    state=None,
):
    """Wie alpha_beta_tt, gibt zusaetzlich (score, best_move, nodes) zurueck.

    Wenn tt None ist, wird eine frische TT angelegt -- praktisch fuer Tests,
    in der echten KI sollte die TT aber zwischen den iterativen Tiefen
    erhalten bleiben.

    `state` ist ein optionaler SearchState mit Killer-Moves + History-Tabelle.
    Wenn None, lauft die Suche genauso wie ohne diese Erweiterungen
    (rueckwaertskompatibel).

    `plies_from_root` -> tiefenabhaengiger Sieg-Score.
    """
    if counter is None:
        counter = [0]
    if tt is None:
        tt = TranspositionTable()

    counter[0] += 1

    # --- TT-Lookup ---------------------------------------------------------
    # Wir koennen den Eintrag nur nutzen, wenn er mindestens so tief war wie
    # unsere aktuelle Anfrage -- sonst ist sein Score weniger verlaesslich.
    alpha_orig = alpha
    tt_best_move = None
    entry = tt.lookup(board)
    if entry is not None and entry.depth >= depth:
        if entry.flag == EXACT:
            return entry.score, entry.best_move, counter[0]
        if entry.flag == LOWER_BOUND:
            alpha = max(alpha, entry.score)
        elif entry.flag == UPPER_BOUND:
            beta = min(beta, entry.score)
        if alpha >= beta:
            return entry.score, entry.best_move, counter[0]
        tt_best_move = entry.best_move
    elif entry is not None:
        # Eintrag zu flach -> nicht verwertbar, aber best_move taugt fuer
        # Move-Ordering.
        tt_best_move = entry.best_move

    # --- Abbruchbedingungen ------------------------------------------------
    term = terminal_score(board, plies_from_root)
    if term is not None:
        return term, None, counter[0]
    if depth == 0:
        return evaluate(board), None, counter[0]

    moves = list(generate_legal_moves(board, board.side_to_move))
    moves = order_moves(
        board,
        moves,
        tt_move=tt_best_move,
        state=state,
        depth=plies_from_root,
    )

    # TT-best_move nach vorn: hoechste Chance auf fruehen Cutoff.
    """if tt_best_move is not None and tt_best_move in moves:
        moves.remove(tt_best_move)
        moves.insert(0, tt_best_move)"""

    # --- Suche -------------------------------------------------------------
    if board.side_to_move == WHITE:
        best_score = float("-inf")
        best_move = None

        for move in moves:
            child = apply_move(board, move)
            score, _, _ = alpha_beta_tt_with_count(
                child,
                depth - 1,
                alpha,
                beta,
                tt,
                counter,
                plies_from_root + 1,
                state,
            )

            if score > best_score:
                best_score = score
                best_move = move

            if best_score > alpha:
                alpha = best_score
            if alpha >= beta:
                if state is not None:
                    state.record_killer(plies_from_root, move)
                    state.record_history(move, depth)
                break
    else:
        best_score = float("+inf")
        best_move = None

        for move in moves:
            child = apply_move(board, move)
            score, _, _ = alpha_beta_tt_with_count(
                child,
                depth - 1,
                alpha,
                beta,
                tt,
                counter,
                plies_from_root + 1,
                state,
            )

            if score < best_score:
                best_score = score
                best_move = move

            if best_score < beta:
                beta = best_score
            if alpha >= beta:
                # History/Killer nur bei echtem Beta-Cutoff -- symmetrisch zum
                # MAX-Knoten und zu pvs.py, konform zur History-Heuristik
                # (nur Cutoff-Zuege bekommen einen Bonus).
                if state is not None:
                    state.record_killer(plies_from_root, move)
                    state.record_history(move, depth)
                break

    # --- TT-Store ----------------------------------------------------------
    # Flag bestimmt sich aus der Lage des Ergebnisses zum ANGEFRAGTEN Fenster:
    # - <= alpha_orig : kein Zug schlug alpha -> wahrer Wert <= best_score (UPPER)
    # - >= beta       : Beta-Cutoff           -> wahrer Wert >= best_score (LOWER)
    # - sonst         : Score lag im Fenster -> EXACT
    if best_score <= alpha_orig:
        flag = UPPER_BOUND
    elif best_score >= beta:
        flag = LOWER_BOUND
    else:
        flag = EXACT

    tt.store(board, depth, best_score, flag, best_move)
    return best_score, best_move, counter[0]
