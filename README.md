# DeepKnight

[![Tests](https://github.com/Robertsvg/deepknight/actions/workflows/tests.yml/badge.svg)](https://github.com/Robertsvg/deepknight/actions/workflows/tests.yml)

A Python engine for Tablut, an asymmetric strategy game played on a 9 x 9
board. DeepKnight combines bitboard move generation, an optimized game-tree
search, and Monte Carlo Tree Search with an optional RAVE/AMAF extension.

## Features

- Three bitboards for attackers, defenders, and the king.
- Minimax and Alpha-Beta baselines for comparison.
- Principal Variation Search, iterative deepening, and a transposition table.
- Capture ordering, killer moves, history scores, and phase-aware time budgets.
- King-safety evaluation, escape lanes, guarded-corner detection, and defender support.
- MCTS with UCT selection, heuristic rollouts, and switchable RAVE statistics.
- Console play, a Tkinter desktop board, FEN import/export, and perft checks.
- A TCP client and a separate rules adapter for the TU Berlin Gameserver.
- Automated tests and reproducible search/self-play tools.

The main playing agent is `AdvancedAI`. `MCTSAI` is an independent search
alternative; RAVE is experimental rather than a guaranteed strength improvement.

## Get Started

Python 3.10 or newer is required. The engine uses only the standard library.
Tkinter is needed for the optional desktop board; some Linux distributions
package it separately.

```bash
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` on PowerShell or
`source .venv/bin/activate` on macOS/Linux, then install the development tools:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests watch_board.py
python -m src.play
```

For the desktop board:

```bash
python -m src.gui
```

## Use the Engine

```python
from src.ai import AdvancedAI, MCTSAI
from src.fen import starting_position
from src.moves import apply_move

board = starting_position()
ai = AdvancedAI(time_limit_s=1.0, max_depth=6)
move = ai.choose_move(board)
if move is not None:
    board = apply_move(board, move)

# Disable RAVE to compare against plain UCT.
mcts = MCTSAI(time_limit_s=0.2, use_rave=False, random_seed=7)
```

All agents share `choose_move(board)`. Moves are zero-based
`(from_row, from_column, to_row, to_column)` tuples. Positive evaluation scores
favor White; negative scores favor Black.

## Benchmarks

```bash
python -m src.benchmark
python -m src.m3_experiments 1.0
python -m src.m4_selfplay --help
```

The legacy module names are retained to keep the original experiment entry
points working. See [benchmarking](docs/benchmarking.md) for protocols,
reference measurements, and limitations. Historical measurements are not
promises about performance on another machine.

## Gameserver

```bash
python -m src.gameserver --host SERVER --port 5050 --lobby deepknight
```

The server is external and is not bundled. The client implements its TCP
protocol using the standard library. See [server integration](docs/server.md)
for hosting and viewer commands.

## Project Layout

```text
src/                  Board, rules, search agents, interfaces, and experiments
tests/                Rules, search, timing, MCTS, and regression tests
docs/architecture.md  Engine design and search techniques
docs/benchmarking.md  Experiment protocol and interpretation
docs/report/          Technical report source adapted from the final project
benchmarks/reference/ Historical search and move-generation measurements
watch_board.py        Live ASCII viewer for gameserver logs
```

## Background

Maintained as a standalone portfolio edition by [Yousef Mousa](https://github.com/Robertsvg).
Based on the [DeepKnight group project](https://github.com/BatuCani/deepknight),
developed with Batuhan Caniberk and Adham Ahmed Mostafa Mohamed Ibrahim at
TU Berlin. See [provenance](docs/provenance.md) for the source revision and
the scope of this edition.
