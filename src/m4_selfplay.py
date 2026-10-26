"""Color-balanced self-play comparisons for MCTS, UCT, and AdvancedAI."""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ai import MCTSAI, AdvancedAI
from src.board import WHITE, Board
from src.fen import starting_position
from src.moves import apply_move, generate_legal_moves
from src.rules import is_game_over


@dataclass
class SelfPlayResult:
    white_ai: str
    black_ai: str
    result: str
    moves: int


def play_match(
    white_ai,
    black_ai,
    max_moves: int = 80,
    *,
    initial_board: Board | None = None,
) -> SelfPlayResult:
    """Play one game and return the result.

    A non-terminal position at the move cap is adjudicated as a draw.
    A supplied initial board is copied, leaving the caller's position intact.
    """
    if max_moves < 0:
        raise ValueError("max_moves must be non-negative")
    board = starting_position() if initial_board is None else initial_board.copy()

    for move_number in range(1, max_moves + 1):
        result = is_game_over(board)
        if result is not None:
            return SelfPlayResult(
                white_ai=white_ai.__class__.__name__,
                black_ai=black_ai.__class__.__name__,
                result=result,
                moves=move_number - 1,
            )

        legal_moves = list(generate_legal_moves(board, board.side_to_move))
        if not legal_moves:
            return SelfPlayResult(
                white_ai=white_ai.__class__.__name__,
                black_ai=black_ai.__class__.__name__,
                result="draw",
                moves=move_number - 1,
            )

        ai = white_ai if board.side_to_move == WHITE else black_ai
        move = ai.choose_move(board)
        if move not in legal_moves:
            loser = board.side_to_move
            result = "black_wins" if loser == WHITE else "white_wins"
            return SelfPlayResult(
                white_ai=white_ai.__class__.__name__,
                black_ai=black_ai.__class__.__name__,
                result=result,
                moves=move_number - 1,
            )

        board = apply_move(board, move)

    return SelfPlayResult(
        white_ai=white_ai.__class__.__name__,
        black_ai=black_ai.__class__.__name__,
        result=is_game_over(board) or "draw",
        moves=max_moves,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games-per-color", type=int, default=1)
    parser.add_argument("--opponent", choices=("advanced", "uct"), default="advanced")
    parser.add_argument("--time", type=float, default=0.2, help="Seconds per move")
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--rollout-depth", type=int, default=20)
    parser.add_argument("--depth", type=int, default=2, help="AdvancedAI depth cap")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-moves", type=int, default=80)
    parser.add_argument(
        "--fixed-iterations",
        action="store_true",
        help="Disable the MCTS wall-clock cap for reproducible iteration budgets",
    )
    parser.add_argument(
        "--output", type=Path, help="Write configuration and results as JSON"
    )
    args = parser.parse_args()
    for name in ("games_per_color", "iterations", "depth", "max_moves"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.time <= 0 or args.rollout_depth < 0:
        parser.error("--time must be positive and --rollout-depth non-negative")

    mcts_time = None if args.fixed_iterations else args.time
    records = []
    outcomes = {"wins": 0, "losses": 0, "draws": 0}
    for game in range(args.games_per_color):
        for candidate_color in ("white", "black"):
            seed = args.seed + game
            candidate = MCTSAI(
                time_limit_s=mcts_time,
                max_iterations=args.iterations,
                rollout_depth=args.rollout_depth,
                random_seed=seed,
                use_rave=True,
            )
            if args.opponent == "uct":
                opponent = MCTSAI(
                    time_limit_s=mcts_time,
                    max_iterations=args.iterations,
                    rollout_depth=args.rollout_depth,
                    random_seed=seed,
                    use_rave=False,
                )
            else:
                opponent = AdvancedAI(time_limit_s=args.time, max_depth=args.depth)

            white, black = (
                (candidate, opponent)
                if candidate_color == "white"
                else (opponent, candidate)
            )
            started = time.perf_counter()
            match = play_match(white, black, max_moves=args.max_moves)
            record = asdict(match)
            record.update(
                candidate_color=candidate_color,
                seed=seed,
                elapsed_s=time.perf_counter() - started,
            )
            records.append(record)
            if match.result == "draw":
                outcomes["draws"] += 1
            elif match.result == f"{candidate_color}_wins":
                outcomes["wins"] += 1
            else:
                outcomes["losses"] += 1
            print(
                f"MCTS+RAVE as {candidate_color} vs {args.opponent}: "
                f"{match.result} after {match.moves} plies (seed {seed})"
            )

    print(f"MCTS+RAVE totals: {outcomes}")
    if args.output is not None:
        config = vars(args).copy()
        config.pop("output")
        payload = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "configuration": config,
            "candidate": "MCTS+RAVE",
            "outcomes": outcomes,
            "games": records,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
