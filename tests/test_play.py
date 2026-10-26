"""Console regressions for malformed input and Windows output encodings."""

import os
import subprocess
import sys

import pytest

from src.play import parse_move


@pytest.mark.parametrize("text", ["", "a-", "-a1", "a0-a1", "j1-a1", "a1-a1-a2"])
def test_parse_move_rejects_malformed_coordinates(text):
    with pytest.raises(ValueError):
        parse_move(text)


def test_parse_move_accepts_case_and_outer_whitespace():
    assert parse_move(" B2-A2 ") == (7, 1, 7, 0)


def test_console_survives_invalid_input_and_white_turn_on_windows_encoding():
    result = subprocess.run(
        [sys.executable, "-m", "src.play"],
        input="a-\nai\nquit\n",
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONIOENCODING="cp1255"),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "Invalid input:" in result.stdout
    assert "AI move:" in result.stdout
    assert "To move: White" in result.stdout
