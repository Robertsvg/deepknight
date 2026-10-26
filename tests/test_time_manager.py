import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import time_manager
from src.time_manager import DEFAULT_SAFETY_MARGIN_S, PHASE_FACTORS, TimeManager


def test_elapsed_uses_monotonic_time(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(1.0, safety_margin_s=0.0)
    now[0] = 100.25

    assert manager.elapsed() == pytest.approx(0.25)


def test_time_left_until_limit(monkeypatch):
    now = [10.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(1.0, safety_margin_s=0.0)
    assert manager.time_left()

    now[0] = 10.999
    assert manager.time_left()

    now[0] = 11.0
    assert not manager.time_left()


def test_hard_limit_caps_requested_time(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(200.0, hard_limit_s=120.0, safety_margin_s=0.0)
    assert manager.limit_s == 120.0

    now[0] = 119.9
    assert manager.time_left()

    now[0] = 120.0
    assert not manager.time_left()


def test_safety_margin_stops_early(monkeypatch):
    now = [50.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(1.0, safety_margin_s=0.1)
    now[0] = 50.89
    assert manager.time_left()

    now[0] = 50.91
    assert not manager.time_left()
    assert manager.remaining() == 0.0


def test_remaining_never_negative(monkeypatch):
    now = [5.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(1.0, safety_margin_s=0.0)
    now[0] = 7.0

    assert manager.remaining() == 0.0


def test_reset_restarts_timer(monkeypatch):
    now = [20.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(1.0, safety_margin_s=0.0)
    now[0] = 20.8
    manager.reset()
    now[0] = 21.0

    assert manager.elapsed() == pytest.approx(0.2)
    assert manager.time_left()


def test_invalid_limits_raise_value_error():
    with pytest.raises(ValueError):
        TimeManager(0)
    with pytest.raises(ValueError):
        TimeManager(1.0, hard_limit_s=0)
    with pytest.raises(ValueError):
        TimeManager(1.0, safety_margin_s=-0.1)


def test_default_safety_margin_stops_before_requested_limit(monkeypatch):
    now = [30.0]
    monkeypatch.setattr(time_manager.time, "monotonic", lambda: now[0])

    manager = TimeManager(1.0)
    assert manager.safety_margin_s == DEFAULT_SAFETY_MARGIN_S

    now[0] = 30.94
    assert manager.time_left()

    now[0] = 30.951
    assert not manager.time_left()


def test_budget_for_phase_uses_configured_factors():
    manager = TimeManager(10.0)

    assert manager.budget_for_phase("opening") == 10.0 * PHASE_FACTORS["opening"]
    assert manager.budget_for_phase("midgame") == 10.0 * PHASE_FACTORS["midgame"]
    assert manager.budget_for_phase("endgame") == 10.0 * PHASE_FACTORS["endgame"]


def test_budget_for_unknown_phase_uses_original_limit():
    manager = TimeManager(10.0)

    assert manager.budget_for_phase("unknown") == 10.0


def test_budget_for_phase_returns_adjusted_requested_limit():
    manager = TimeManager(100.0, hard_limit_s=110.0)

    assert manager.budget_for_phase("midgame") == 100.0 * PHASE_FACTORS["midgame"]
