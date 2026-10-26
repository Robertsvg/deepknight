# Benchmarking

## Correctness

```bash
python -m pytest -q
python -m compileall -q src tests
```

The inherited final upstream snapshot passes 138 tests. The portfolio edition
adds regression coverage; use pytest's current result rather than treating
the historical count as a fixed badge. Tests demonstrate specified behavior,
not tournament strength.

## Move Generation and Search

```bash
python -m src.benchmark
python -m src.m3_experiments 1.0
```

Move-generation benchmarks write a platform-specific CSV in the working
directory. Search experiments compare seven configurations across six FEN
positions. Keep the Python version, hardware, time budget, position, and
completed depth with each result. Compare nodes at equal depth; counts from
different completed depths do not establish a pruning speedup.

[Reference output](../benchmarks/reference/search-results.md) and the adjacent
CSV files preserve original project measurements. These are historical data,
not new runs of this edition. In the original start-position run, AdvancedAI
visited more nodes than the Alpha-Beta baseline at the same completed depth;
the optimizations are position-dependent.

## MCTS Comparisons

```bash
python -m src.m4_selfplay --games-per-color 2 --opponent advanced --output selfplay-results.json
python -m src.m4_selfplay --games-per-color 2 --opponent uct --output selfplay-results-rave.json
```

Use both color assignments and multiple seeds. The UCT opponent disables RAVE
while retaining the same rollout and iteration settings. A fixed iteration
budget without a wall-clock cap is reproducible for MCTS comparisons; an equal
time budget measures practical throughput and may complete different numbers
of iterations. The JSON includes the configuration and individual outcomes.
Move limits are adjudication limits, not proof of a game-theoretic draw.

The original two-game MCTS/AdvancedAI comparison ended 1:1, with Black winning
both games. This small sample cannot establish equal strength or a general
attacker advantage. The final project report also records no demonstrated
RAVE improvement under its small test budget. Larger samples and timing data
are needed before making strength claims.

The [portfolio smoke run](../benchmarks/portfolio-rave-smoke.json) uses seed 7,
200 iterations per move, rollout depth 8, both color assignments, and a
12-ply cap. Both games were adjudicated draws at that cap. This checks that
the comparison tool runs and records results; it is not a strength benchmark.

## Historical Server Checks

The original project report records zero board divergences in 1,000 random
games (152,000 moves) compared with the external gameserver, plus wins in
both color roles after king-safety changes. The external verification harness
and opponents are not bundled, so these figures are retained as historical
report observations rather than reproducible local test results.
