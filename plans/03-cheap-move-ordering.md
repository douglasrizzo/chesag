# Plan 03: Cheap Move Ordering First

## Why This Plan Exists

Recommendation 3 is to stop treating move ordering like mini-search. Good move ordering should
usually be built from cheap, local heuristics before any expensive evaluation is attempted.

## Current Behavior

[`src/chesag/move_priority.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/move_priority.py)
currently orders moves by pushing each move and calling:

- `quick_evaluate()`
- full `evaluate(..., include_move_bonus=True)`

That means every ordering pass is already spending a meaningful part of a leaf-evaluation budget.
Because ordering is performed at many interior nodes, this work multiplies rapidly.

## What Is Wrong With That

Move ordering only needs to answer:

- which moves are likely worth searching first

It does not need to answer:

- what is the full positional value of the resulting board

By using full board evaluation for ordering, the search is paying a large fixed cost before it
gets the pruning benefit. In many engines, ordering is dominated by very cheap signals:

- transposition-table move
- winning captures
- promotions
- checks
- killer moves
- history heuristic

Only after those are exhausted does more expensive scoring become attractive.

## Proposed Solution

Build move ordering as a layered heuristic pipeline:

1. TT move first
1. tactical forcing moves
   - promotions
   - good captures
   - checking moves
1. killer moves
1. history heuristic
1. optional cheap static tiebreak

This means `move_priority.py` becomes a true heuristic ordering module rather than a repeated
full evaluator wrapper.

## Expected Gains

- much faster alpha-beta node expansion
- lower MCTS child-selection overhead if reused there
- better pruning efficiency because the good tactical moves still rise to the top

This is likely one of the largest raw speed wins after fixing minimax correctness.

## Implementation Plan

1. Define an explicit ordering score composed of cheap terms.
1. Add TT move support once the minimax TT lands.
1. Implement capture scoring using MVV-LVA and consider SEE later if needed.
1. Boost promotions and checking moves.
1. Integrate killer/history state meaningfully.
1. Keep any evaluator-based tiebreak optional and very cheap.
1. Benchmark ordering cost directly on representative positions.

## Validation

- ordering tests that assert tactical moves rise above quiet moves in controlled positions
- timing comparison of ordering on midgame positions
- alpha-beta node-count comparison with and without the new ordering pipeline

## After Implementation

Before considering this plan done:

1. Write or update tests covering all changed behavior.
2. Run the full quality gate in order:
   - `uv run ruff check --fix`
   - `uv run ruff format`
   - `uv run ruff check`
   - `uv run ty check`
   - `uv run pytest`
3. All checks must pass cleanly with no new failures.

## Risks

- overly naive capture ordering can still prioritize losing captures
- adding too many heuristic layers without benchmarks can make the code harder to tune
