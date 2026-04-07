# AGENTS.md

## Overview

- `chesag` is a small Python chess engine playground with multiple agents: random, minimax, MCTS, and Stockfish-backed play.
- The main entrypoint is [`src/chesag/cli.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/cli.py).
- Source layout is `src/chesag`.
- Core gameplay lives under [`src/chesag/game`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/game).
- Search and evaluation logic live under [`src/chesag/agents`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents), [`src/chesag/evaluation.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/evaluation.py), and [`src/chesag/position_key.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/position_key.py).

## Environment

- Python is managed with `uv`.
- Install dependencies with `uv sync`.
- Install development tooling with `uv sync --group dev`.
- Run the CLI with `uv run chesag`.
- The package is installed from `src/chesag`; prefer normal imports over path hacks in tests or scripts.
- Typical smoke command:

```bash
uv run chesag play minimax --player2 mcts --games 2
```

## Quality Tools

- Lint with `uv run ruff check --fix`.
- Format with `uv run ruff format`.
- Type-check with `uv run ty check`.
- Run hooks with `uv run pre-commit run --all-files`.
- Run tests with `uv run pytest`.
- In upcoming phases, use these tools by default after code changes:
  - `ruff check --fix` first, so automatic fixes land before manual cleanup
  - `ruff format`
  - `ruff check`
  - `ty check` for touched Python modules when practical
  - `pytest` for any covered behavior or new tests
- Keep behavioral changes separate from broad lint cleanup unless the phase explicitly targets cleanup.

## Repository Map

- [`src/chesag/cli.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/cli.py): CLI for `play`, `replay`, and placeholder `train`.
- [`src/chesag/game/game.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/game/game.py): main game loop and result generation.
- [`src/chesag/game/results.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/game/results.py): player-relative result formatting.
- [`src/chesag/game/statistics.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/game/statistics.py): multi-game reporting.
- [`src/chesag/agents/minimax.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/minimax.py): alpha-beta / quiescence implementation.
- [`src/chesag/agents/mcts`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/mcts): MCTS node, searcher, and config.
- [`src/chesag/evaluation.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/evaluation.py): tiered leaf, ordering, and rollout evaluation helpers.
- [`src/chesag/benchmarks.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/benchmarks.py): local benchmark and smoke-match helpers for search validation.
- [`src/chesag/move_priority.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/move_priority.py): cheap-first move ordering with TT, tactical, killer, and history heuristics.
- [`src/chesag/position_key.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/position_key.py): shared runtime position key helper for search caches.
- [`src/chesag/viewer.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/viewer.py): PyQt6 board viewer.
- [`src/chesag/replay.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/replay.py): PGN replay path.

## Working Rules

- Prefer `rg` for searches and `uv run chesag ...` for CLI execution.
- Prefer `uv run ruff check --fix`, `uv run ruff format`, `uv run ty check`, and `uv run pytest` over ad hoc alternatives.
- Use `ruff` auto-fixes before making manual style-only edits.
- Use `python-chess` semantics carefully. `Move.null()` is not the same as “no move”; pushing it mutates the board.
- Treat move-evaluation sign conventions as high risk. Verify perspective handling whenever touching minimax, MCTS, or resignation logic.
- Preserve current logging style unless there is a clear reason to change it.
- The repo is gaining automated checks; in later phases, do not finish code changes without running the relevant tooling and tests.

## Known Fragile Areas

- [`src/chesag/game/game.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/game/game.py): resignation is handled before `board.push()`, so keep that contract intact if the loop is refactored.
- [`src/chesag/agents/random.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/random.py): resignation/evaluation path is currently easy to break because it depends on evaluation perspective.
- [`src/chesag/evaluation.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/evaluation.py): evaluation-tier counters are global process state; reset them before benchmarks or assertions that depend on exact counts.
- [`src/chesag/move_priority.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/move_priority.py): move ordering is central to both minimax and MCTS performance, so validate it with actual per-move scoring.
- [`src/chesag/agents/mcts/algorithm.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/mcts/algorithm.py): cache normalization and backpropagation perspective handling are easy places to introduce silent strength regressions.
- [`src/chesag/replay.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/replay.py): replay and viewer integration should be smoke-tested after any UI or constructor change.

## Review Expectations

- Default to code-review mode: prioritize bugs, behavioral regressions, wrong assumptions, and missing verification.
- When reporting findings, include file references with line numbers.
- Separate confirmed runtime failures from architecture or quality concerns.
- If you cannot verify a behavior locally, say so explicitly.
