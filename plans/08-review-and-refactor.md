# Plan 08: Codebase Review And Refactor

## Why This Plan Exists

After plans 01–08 land, the codebase will have gone through significant behavioral changes across
search, evaluation, move ordering, and MCTS. This final plan is a deliberate, full-pass review
to consolidate those changes into a clean, coherent package before further feature work.

The questions to answer during this plan are:

- Is there duplicated logic that should be a single shared implementation?
- Are any modules taking on too many responsibilities?
- Are there patterns applied inconsistently across similar code?
- Is the module structure still a good reflection of the domain?
- Is the public API (agents, evaluation, move ordering) expressed at the right level of abstraction?

## Scope

### DRY Review

Look for logic that is expressed more than once across the codebase:

- Perspective/sign handling: minimax, MCTS, and evaluation all deal with color-relative scores.
  After the earlier plans, this should be converging — check whether any redundant perspective
  logic remains or if a small shared utility would eliminate duplication.
- Board-push / board-pop patterns: audit for consistent use, especially in evaluation and ordering.
- Resignation logic: currently appears in both `MinimaxAgent` and `MCTSAgent`. Evaluate whether
  it belongs in the agent base or in a shared helper.
- Terminal-state detection: several places check `board.is_game_over()` independently; confirm
  whether a single authoritative path covers all callers.

### Design Pattern Opportunities

Review whether any of these patterns would reduce complexity or clarify responsibility:

- **Strategy / Registry for agents**: `cli.py` constructs agents by name string. A registry
  mapping names to constructors would remove the branching and make adding new agents a
  one-liner. Only worth introducing if the dispatch is messy after earlier changes.
- **Evaluation as a typed protocol**: after plan 02 introduces explicit evaluation tiers, check
  whether defining a small `Evaluator` protocol would clarify call sites or if plain functions
  are cleaner.
- **Search stats / instrumentation**: `MinimaxAgent.last_search` is an ad-hoc dict. After
  earlier phases, review whether a small dataclass or named tuple would be cleaner without
  adding unnecessary abstraction.
- **Agent base class contract**: `BaseAgent` currently declares `get_move`. Review whether
  `close()` (currently only on `MCTSAgent`) should be part of the interface, or whether a
  context-manager protocol is more appropriate.

### Module Structure Review

Walk each module and ask whether its name, location, and public surface match what it actually does:

- `evaluation.py`: after tier separation, confirm the module's public API is clear and that
  internal helpers are not leaking into the public surface.
- `move_priority.py`: after plans 03 and 04 change the ordering pipeline significantly, reassess
  whether the module is coherent or whether parts belong closer to the search agents.
- `agents/mcts/`: three files (`agent.py`, `algorithm.py`, `node.py`) cover config, search loop,
  and tree node. Confirm responsibilities are still well-separated after earlier MCTS changes.
- `game/`: `game.py`, `results.py`, `statistics.py` — check if any cross-cutting logic has
  drifted between these after earlier fixes.
- `cli.py`: confirm it remains a thin entrypoint and has not accumulated business logic.

### Simplification Pass

After behavioral changes, some code may be:

- Longer than it needs to be because of scaffolding that is no longer necessary.
- Harder to read because intermediate variables or helper methods were added during fixes and
  are now redundant.
- Over-engineered for the actual use case (e.g., config classes with only one live field).

Apply targeted simplifications where complexity is not earning its keep.

## What Is Out Of Scope

- New search features or evaluation improvements — those belong in follow-up plans.
- Large renamings or restructurings without strong justification.
- Chasing style uniformity for its own sake.

## Implementation Plan

1. Read every module end-to-end after the earlier plans have landed.
2. For each area above, write down the finding before touching code.
3. Group changes into independent, reviewable commits:
   - DRY consolidations
   - design-pattern introductions (only if clearly beneficial)
   - module restructuring
   - simplification and cleanup
4. Do not mix behavioral changes with structural ones in the same commit.
5. Update `AGENTS.md` if the module map or working rules have changed.

## Validation

- The full test suite must pass throughout every commit in this plan.
- No search-behavior regressions: run smoke games comparing agents before and after.
- Confirm `AGENTS.md` reflects the current state of the repo at the end of this plan.

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
