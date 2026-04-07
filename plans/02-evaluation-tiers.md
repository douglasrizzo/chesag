# Plan 02: Evaluation Tiers For Search

## Why This Plan Exists

The evaluator is being used for too many purposes:

- root and leaf evaluation
- move ordering
- quiescence standing pat
- rollout move weighting
- rollout early stopping

Those use cases do not need the same cost profile. Recommendation 6 is to split the evaluator
into explicit cost tiers.

## Current Behavior

[`src/chesag/evaluation.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/evaluation.py)
provides:

- `evaluate()`: feature-rich positional evaluation
- `quick_evaluate()`: a reduced evaluation, but still based on full board feature calculations

Even the “quick” path still includes:

- piece counting
- bishop-pair logic
- center-control attacker scans

The full path additionally includes:

- passed-pawn scans
- king-safety scans
- mobility computation for both colors
- move bonus logic that may pop and push moves

These routines are called from high-frequency search paths, not just from expensive leaves.

## What Is Wrong With That

Search code needs different tools for different jobs:

- move ordering wants “cheap and roughly correlated”
- leaf evaluation wants “expensive enough to matter”
- rollout policy wants “extremely cheap”

When one evaluator serves all three jobs, one of two bad outcomes happens:

1. The evaluator becomes too weak for leaves.
1. The evaluator becomes too expensive for ordering and rollouts.

Right now the second problem is more visible.

## Proposed Evaluation Model

Create explicit tiers, for example:

- `order_evaluate()`
  - material delta
  - capture/promotion/check signals
  - maybe simple PST or center bonus
- `leaf_evaluate()`
  - the current richer positional terms
  - used by minimax leaves and direct MCTS leaf evaluation
- `rollout_evaluate()` or remove heavy rollouts entirely
  - if rollouts remain, use a minimal score

The important part is not the exact names. The important part is that call sites must choose a
known cost tier intentionally.

## Expected Gains

- lower search overhead
- clearer performance profiling
- less temptation to reuse an expensive function in the wrong place
- easier future tuning because each tier can be benchmarked separately

## Implementation Plan

1. Audit every call site of `evaluate()` and `quick_evaluate()`.
1. Classify each call site as ordering, leaf, quiescence, or rollout.
1. Introduce explicit evaluation functions or profiles for those use cases.
1. Move current feature toggles behind clearer wrappers so call sites stop assembling ad hoc evals.
1. Add benchmarks or timing counters around evaluator usage.
1. Update tests so evaluator contracts are about symmetry and relative ranking, not exact magic numbers unless stable.

## Validation

- profiling before/after on fixed search positions
- unit tests for symmetry and terminal scoring
- node-per-second comparisons for minimax and MCTS

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

- an overly cheap ordering evaluator can hurt pruning enough to lose strength
- changing evaluator tiers without good profiling can just move cost around instead of reducing it
