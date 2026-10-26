"""Time management helpers for M2 search."""

import time

DEFAULT_HARD_LIMIT_S = 120.0
DEFAULT_SAFETY_MARGIN_S = 0.05
PHASE_FACTORS = {
    "opening": 0.7,
    "midgame": 1.3,
    "endgame": 0.9,
}


class TimeManager:
    """Tracks elapsed time and enforces a soft limit capped by a hard stop."""

    def __init__(
        self,
        time_limit_s: float,
        hard_limit_s: float = DEFAULT_HARD_LIMIT_S,
        safety_margin_s: float = DEFAULT_SAFETY_MARGIN_S,
    ) -> None:
        if time_limit_s <= 0:
            raise ValueError("time_limit_s must be positive")
        if hard_limit_s <= 0:
            raise ValueError("hard_limit_s must be positive")
        if safety_margin_s < 0:
            raise ValueError("safety_margin_s must not be negative")

        self.time_limit_s = float(time_limit_s)
        self.hard_limit_s = float(hard_limit_s)
        self.safety_margin_s = float(safety_margin_s)
        self.limit_s = min(self.time_limit_s, self.hard_limit_s)
        self.search_limit_s = max(0.0, self.limit_s - self.safety_margin_s)
        self.start_time = time.monotonic()

    def elapsed(self) -> float:
        """Return seconds elapsed since this manager was created."""
        return time.monotonic() - self.start_time

    def time_left(self) -> bool:
        """Return True while search may continue."""
        return self.elapsed() < self.search_limit_s

    def remaining(self) -> float:
        """Return remaining seconds before the effective limit is reached."""
        return max(0.0, self.search_limit_s - self.elapsed())

    def budget_for_phase(self, phase: str) -> float:
        """Return a time budget adjusted for the current game phase."""
        factor = PHASE_FACTORS.get(phase, 1.0)
        return self.time_limit_s * factor

    def reset(self) -> None:
        """Restart the timer with the same limits."""
        self.start_time = time.monotonic()
