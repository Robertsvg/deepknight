"""Principal Variation Search for Tablut.

Scores follow the project convention:
- high scores are good for White
- low scores are good for Black

Optional integrations:
- Transposition Table (TT) via `tt` parameter
- Killer Moves + History Heuristic via SearchState `state` parameter

Both integrations are optional; plain pvs(board, depth) remains available.
"""

from src.board import WHITE
from src.evaluation import evaluate, terminal_score
from src.move_ordering import order_moves
from src.moves import apply_move, generate_legal_moves
from src.transposition_table import EXACT, LOWER_BOUND, UPPER_BOUND

NULL_WINDOW = 1.0


def pvs(board, depth, alpha=float("-inf"), beta=float("+inf"), counter=None):
    """Run Principal Variation Search and return (score, best_move)."""
    score, move, _ = pvs_with_count(board, depth, alpha, beta, counter)
    return score, move


def pvs_with_count(
    board,
    depth,
    alpha=float("-inf"),
    beta=float("+inf"),
    counter=None,
    plies_from_root=0,
    tt=None,
    state=None,
):
    """Run PVS and return (score, best_move, visited_nodes).

    `plies_from_root` -> tiefenabhaengiger Sieg-Score.
    `tt`              -> optionale Transposition Table (M3-Kombi).
    `state`           -> optionaler SearchState mit Killer + History.
    """
    if counter is None:
        counter = [0]

    counter[0] += 1

    # --- TT-Lookup ---------------------------------------------------------
    alpha_orig = alpha
    tt_best_move = None
    if tt is not None:
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
            tt_best_move = entry.best_move

    # --- Abbruch -----------------------------------------------------------
    term = terminal_score(board, plies_from_root)
    if term is not None:
        return term, None, counter[0]
    if depth == 0:
        return evaluate(board), None, counter[0]

    moves = list(generate_legal_moves(board, board.side_to_move))
    if not moves:
        return evaluate(board), None, counter[0]

    # Eine einzige order_moves-Pass: kombiniert die taktische Basis-Sortierung
    # (Schlaege, Koenig-Richtung-Ecke) mit TT-best_move + Killer + History
    # falls tt/state vorhanden sind. depth=plies_from_root, weil Killer-
    # Tabellen nach Suchtiefe von der Wurzel indiziert werden.
    moves = order_moves(
        board,
        moves,
        tt_move=tt_best_move if tt is not None else None,
        state=state,
        depth=plies_from_root,
    )

    if board.side_to_move == WHITE:
        best_score, best_move = _pvs_max(
            board,
            moves,
            depth,
            alpha,
            beta,
            counter,
            plies_from_root,
            tt,
            state,
        )
    else:
        best_score, best_move = _pvs_min(
            board,
            moves,
            depth,
            alpha,
            beta,
            counter,
            plies_from_root,
            tt,
            state,
        )

    # --- TT-Store ----------------------------------------------------------
    if tt is not None and best_move is not None:
        if best_score <= alpha_orig:
            flag = UPPER_BOUND
        elif best_score >= beta:
            flag = LOWER_BOUND
        else:
            flag = EXACT
        tt.store(board, depth, best_score, flag, best_move)

    return best_score, best_move, counter[0]


def _pvs_max(board, moves, depth, alpha, beta, counter, plies_from_root, tt, state):
    best_score = float("-inf")
    best_move = None
    first_child = True

    for move in moves:
        child = apply_move(board, move)

        if first_child:
            score, _, _ = pvs_with_count(
                child,
                depth - 1,
                alpha,
                beta,
                counter,
                plies_from_root + 1,
                tt,
                state,
            )
            first_child = False
        else:
            score, _, _ = pvs_with_count(
                child,
                depth - 1,
                alpha,
                min(beta, alpha + NULL_WINDOW),
                counter,
                plies_from_root + 1,
                tt,
                state,
            )
            if alpha < score < beta:
                score, _, _ = pvs_with_count(
                    child,
                    depth - 1,
                    alpha,
                    beta,
                    counter,
                    plies_from_root + 1,
                    tt,
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

    return best_score, best_move


def _pvs_min(board, moves, depth, alpha, beta, counter, plies_from_root, tt, state):
    best_score = float("+inf")
    best_move = None
    first_child = True

    for move in moves:
        child = apply_move(board, move)

        if first_child:
            score, _, _ = pvs_with_count(
                child,
                depth - 1,
                alpha,
                beta,
                counter,
                plies_from_root + 1,
                tt,
                state,
            )
            first_child = False
        else:
            score, _, _ = pvs_with_count(
                child,
                depth - 1,
                max(alpha, beta - NULL_WINDOW),
                beta,
                counter,
                plies_from_root + 1,
                tt,
                state,
            )
            if alpha < score < beta:
                score, _, _ = pvs_with_count(
                    child,
                    depth - 1,
                    alpha,
                    beta,
                    counter,
                    plies_from_root + 1,
                    tt,
                    state,
                )

        if score < best_score:
            best_score = score
            best_move = move

        if best_score < beta:
            beta = best_score
        if alpha >= beta:
            if state is not None:
                state.record_killer(plies_from_root, move)
                state.record_history(move, depth)
            break

    return best_score, best_move
