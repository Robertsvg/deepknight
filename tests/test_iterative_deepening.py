from src.iterative_deepening import iterative_deepening


class FakeTimeManager:
    def __init__(self):
        self._elapsed = 0.0
        self.allowed = True

    def time_left(self):
        return self.allowed

    def elapsed(self):
        return self._elapsed

    def set_elapsed(self, value):
        self._elapsed = value


def test_iterative_deepening_returns_deepest_completed_result():
    tm = FakeTimeManager()

    def fake_search(board, depth, time_manager):
        time_manager.set_elapsed(depth * 0.1)
        return depth * 10, f"move-depth-{depth}", depth * 100

    result = iterative_deepening(
        board=None,
        search_fn=fake_search,
        time_manager=tm,
        max_depth=3,
    )

    assert result.depth == 3
    assert result.score == 30
    assert result.best_move == "move-depth-3"
    assert result.nodes == 300


def test_iterative_deepening_ignores_unfinished_depth():
    tm = FakeTimeManager()

    def fake_search(board, depth, time_manager):
        if depth == 3:
            raise TimeoutError()
        return depth * 10, f"move-depth-{depth}", depth * 100

    result = iterative_deepening(
        board=None,
        search_fn=fake_search,
        time_manager=tm,
        max_depth=5,
    )

    assert result.depth == 2
    assert result.score == 20
    assert result.best_move == "move-depth-2"
    assert result.nodes == 200
