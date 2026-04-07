# Plan 04: Reuse Ordering State Instead Of Recomputing It

## Why This Plan Exists

Recommendation 9 is about finally using the move-ordering state that already exists in the code.
The current implementation tracks history and killer data, but the ordering pipeline does not
benefit enough from it.

## Current Behavior

[`HeuristicMovePrioritizer`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/move_priority.py#L11)
stores:

- `killer_moves`
- `history_heuristic`

But in practice:

- `record_history()` updates history only on cutoffs
- `order_moves()` does not rank moves from these structures in a primary way
- MCTS nodes instantiate fresh prioritizers, so state reuse is fragmented

## What Is Wrong With That

History and killer heuristics matter because they encode search experience:

- killer moves remember quiet moves that caused cutoffs at a depth
- history heuristic remembers moves that were repeatedly useful across the tree

If that state is not reused in actual ordering, the engine keeps re-learning the same lesson
within a single search or across similar searches.

## Proposed Solution

- redesign `order_moves()` to accept contextual data such as depth and TT move
- promote killer and history scores into the main sort key
- define clear ownership of ordering state:
  - per-search state for minimax
  - possibly shared immutable heuristics or no reuse for MCTS, depending on final design
- avoid constructing a brand-new prioritizer per MCTS node unless there is a strong reason

## Expected Gains

- better alpha-beta pruning after the first few branches are explored
- more stable move ordering across the search tree
- less repeated work from evaluator-based ordering

This is lower impact than the earlier plans, but it becomes valuable once cheap ordering is in place.

## Implementation Plan

1. Redefine the ordering API to accept `depth`, `tt_move`, and optional context.
1. Make killer/history terms part of the main ordering score.
1. Scope move-ordering state to a search session rather than to isolated objects where practical.
1. Remove or justify duplicated prioritizer instances in MCTS.
1. Add tests proving that recorded killer/history data changes the next ordering decision.

## Validation

- targeted unit tests for history and killer influence
- alpha-beta node-count comparison with ordering-state reuse enabled

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

- stale ordering state can become noise if scoped too broadly
- MCTS may not benefit from the same reuse patterns as minimax
