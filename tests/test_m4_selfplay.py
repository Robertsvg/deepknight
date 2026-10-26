"""Smoke tests for the M4 self-play helper."""

from src.ai import MCTSAI, RandomAI
from src.fen import parse_fen, to_fen
from src.m4_selfplay import play_match


def test_play_match_returns_result_object():
    white = MCTSAI(
        time_limit_s=1.0,
        max_iterations=5,
        rollout_depth=3,
        random_seed=1,
    )
    black = RandomAI()

    result = play_match(white, black, max_moves=2)

    assert result.white_ai == "MCTSAI"
    assert result.black_ai == "RandomAI"
    assert result.result in {"white_wins", "black_wins", "draw"}
    assert 0 <= result.moves <= 2


def test_win_on_last_allowed_move_is_not_reported_as_draw():
    board = parse_fen("9/9/9/9/9/9/1r7/9/1K7 w 0 1")
    before = to_fen(board)

    class WinningAI:
        def choose_move(self, position):
            return (8, 1, 8, 0)

    result = play_match(WinningAI(), RandomAI(), max_moves=1, initial_board=board)
    assert result.result == "white_wins"
    assert result.moves == 1
    assert to_fen(board) == before


def test_selfplay_cli_exports_color_balanced_results(tmp_path):
    import json
    import subprocess
    import sys

    output = tmp_path / "results.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.m4_selfplay",
            "--opponent",
            "uct",
            "--games-per-color",
            "1",
            "--iterations",
            "1",
            "--rollout-depth",
            "0",
            "--max-moves",
            "1",
            "--fixed-iterations",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert {game["candidate_color"] for game in payload["games"]} == {"white", "black"}
    assert len(payload["games"]) == 2
    assert sum(payload["outcomes"].values()) == 2
    assert payload["configuration"]["fixed_iterations"] is True
