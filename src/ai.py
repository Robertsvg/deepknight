"""KI-Klassen fuer Tablut.

- RandomAI: zufaelliger Zug (M1 Dummy-KI)
- MinimaxAI: Minimax mit iterativer Tiefensuche
- AlphaBetaAI: Alpha-Beta mit iterativer Tiefensuche, Move-Ordering, Zeitmanagement (M2)
- PVSAI: Principal Variation Search mit Spielphasen-Zeitmanagement (M3)
- AlphaBetaTTAI: Alpha-Beta mit Transposition Table (M3)
- AdvancedAI: PVS + TT + Killer Moves + History + Spielphasen-Zeitmanagement
- MCTSAI: Monte Carlo Tree Search mit UCT und optionalem RAVE
"""

import random
from typing import Optional

from src.alpha_beta import alpha_beta
from src.alpha_beta_tt import alpha_beta_tt_with_count
from src.board import Board
from src.evaluation import WIN_SCORE, game_phase
from src.iterative_deepening import iterative_deepening
from src.mcts import MCTSResult, mcts_with_stats
from src.minimax import minimax
from src.moves import generate_legal_moves
from src.pvs import pvs_with_count
from src.search_state import SearchState
from src.time_manager import TimeManager
from src.transposition_table import TranspositionTable

Move = Optional[tuple[int, int, int, int]]


def random_move(board: Board) -> Move:
    moves = list(generate_legal_moves(board, board.side_to_move))
    if not moves:
        return None
    return random.choice(moves)


class RandomAI:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def choose_move(self, board: Board) -> Move:
        return random_move(board)


class MinimaxAI:
    """Minimax-Suche mit iterativer Tiefensuche und Zeitmanagement.

    Wird fuer den Cutoff-Vergleich in den M2-Benchmarks gebraucht.
    """

    def __init__(
        self, time_limit_s: float = 1.0, max_depth: Optional[int] = None
    ) -> None:
        self.time_limit_s = time_limit_s
        self.max_depth = max_depth
        self.last_result = None

    def choose_move(self, board: Board) -> Move:
        tm = TimeManager(self.time_limit_s)

        def search_fn(b, depth, time_manager):
            score, move = minimax(b, depth)
            return score, move, 0

        self.last_result = iterative_deepening(
            board,
            search_fn,
            tm,
            max_depth=self.max_depth,
        )
        return self.last_result.best_move


class AlphaBetaAI:
    """Alpha-Beta-Suche mit iterativer Tiefensuche, Move-Ordering und Zeitmanagement.

    Das ist die eigentliche KI fuer M2.
    """

    def __init__(
        self,
        time_limit_s: float = 1.0,
        max_depth: Optional[int] = None,
        use_ordering: bool = True,
    ) -> None:
        self.time_limit_s = time_limit_s
        self.max_depth = max_depth
        self.use_ordering = use_ordering
        self.last_result = None

    def choose_move(self, board: Board) -> Move:
        tm = TimeManager(self.time_limit_s)

        def search_fn(b, depth, time_manager):
            score, move = alpha_beta(b, depth)
            return score, move, 0

        self.last_result = iterative_deepening(
            board,
            search_fn,
            tm,
            max_depth=self.max_depth,
        )
        return self.last_result.best_move


class AlphaBetaTTAI:
    """Alpha-Beta mit Transposition Table, Iterative Deepening und Zeitmanagement.

    Die TT bleibt ueber alle Tiefen einer einzelnen choose_move()-Entscheidung
    erhalten -- das ist der ganze Witz: Tiefe 2 profitiert von dem, was Tiefe 1
    schon weiss. Zwischen Zuegen leeren wir sie aber (vorsichtshalber, weil
    der Score-Vergleich tiefenabhaengig sein kann sobald evaluation tiefenabh.
    wird).
    """

    def __init__(
        self, time_limit_s: float = 1.0, max_depth: Optional[int] = None
    ) -> None:
        self.time_limit_s = time_limit_s
        self.max_depth = max_depth
        self.tt = TranspositionTable()
        self.last_result = None

    def choose_move(self, board: Board) -> Move:
        tm = TimeManager(self.time_limit_s)
        self.tt.clear()

        def search_fn(b, depth, time_manager):
            score, move, nodes = alpha_beta_tt_with_count(
                b, depth, -WIN_SCORE, WIN_SCORE, self.tt
            )
            return score, move, nodes

        self.last_result = iterative_deepening(
            board,
            search_fn,
            tm,
            max_depth=self.max_depth,
        )
        return self.last_result.best_move


class PVSAI:
    """PVS-Suche mit iterativer Tiefensuche und Spielphasen-Zeitmanagement."""

    def __init__(
        self, time_limit_s: float = 1.0, max_depth: Optional[int] = None
    ) -> None:
        self.time_limit_s = time_limit_s
        self.max_depth = max_depth
        self.last_result = None
        self.last_phase = None
        self.last_phase_budget = None

    def choose_move(self, board: Board) -> Move:
        base_timer = TimeManager(self.time_limit_s)
        self.last_phase = game_phase(board)
        self.last_phase_budget = base_timer.budget_for_phase(self.last_phase)
        tm = TimeManager(
            self.last_phase_budget,
            hard_limit_s=base_timer.hard_limit_s,
            safety_margin_s=base_timer.safety_margin_s,
        )

        def search_fn(b, depth, time_manager):
            score, move, nodes = pvs_with_count(b, depth)
            return score, move, nodes

        self.last_result = iterative_deepening(
            board,
            search_fn,
            tm,
            max_depth=self.max_depth,
        )
        return self.last_result.best_move


class AdvancedAI:
    """M3 Kombi-KI: PVS + TT + Killer Moves + History + Spielphasen-Zeitmanagement.

    Diese KI vereint vier Such- und Zeitmanagement-Techniken:
    - Principal Variation Search (komplex)       -- Null-Window-Suche nach erstem Zug
    - Transposition Table (komplex)              -- Wiederverwendung tieferer Suchergebnisse
    - Killer Moves + History Heuristic           -- besseres Move-Ordering
    - Spielphasen-Zeitmanagement                 -- Budget je nach Eroeffnung/Mid/End
    - Begrenztes AB-Fenster [-WIN_SCORE, +WIN_SCORE] statt +/-inf

    TT und SearchState bleiben ueber alle Iterative-Deepening-Tiefen erhalten.
    Vor jedem neuen choose_move() werden beide geleert.
    """

    def __init__(
        self, time_limit_s: float = 1.0, max_depth: Optional[int] = None
    ) -> None:
        self.time_limit_s = time_limit_s
        self.max_depth = max_depth
        self.tt = TranspositionTable()
        self.state = SearchState()
        self.last_result = None
        self.last_phase = None
        self.last_phase_budget = None

    def choose_move(self, board: Board) -> Move:
        base_timer = TimeManager(self.time_limit_s)
        self.last_phase = game_phase(board)
        self.last_phase_budget = base_timer.budget_for_phase(self.last_phase)
        tm = TimeManager(
            self.last_phase_budget,
            hard_limit_s=base_timer.hard_limit_s,
            safety_margin_s=base_timer.safety_margin_s,
        )

        self.tt.clear()
        self.state.reset()

        def search_fn(b, depth, time_manager):
            score, move, nodes = pvs_with_count(
                b,
                depth,
                -WIN_SCORE,
                WIN_SCORE,
                None,
                0,
                self.tt,
                self.state,
            )
            return score, move, nodes

        self.last_result = iterative_deepening(
            board,
            search_fn,
            tm,
            max_depth=self.max_depth,
        )
        return self.last_result.best_move


class MCTSAI:
    """Monte Carlo search with optional RAVE and deterministic iteration limits."""

    def __init__(
        self,
        time_limit_s: Optional[float] = 1.0,
        max_iterations: Optional[int] = None,
        rollout_depth: int = 80,
        exploration: float = 1.4142135623730951,
        random_seed: Optional[int] = None,
        use_rave: bool = True,
    ) -> None:
        self.time_limit_s = time_limit_s
        self.max_iterations = max_iterations
        self.rollout_depth = rollout_depth
        self.exploration = exploration
        self.random_seed = random_seed
        self.use_rave = use_rave
        self.last_result: Optional[MCTSResult] = None

    def choose_move(self, board: Board) -> Move:
        self.last_result = mcts_with_stats(
            board,
            time_limit_s=self.time_limit_s,
            max_iterations=self.max_iterations,
            rollout_depth=self.rollout_depth,
            exploration=self.exploration,
            random_seed=self.random_seed,
            use_rave=self.use_rave,
        )
        return self.last_result.best_move
