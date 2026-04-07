# Plan 06: Make The MCTS Configuration Honest

## Why This Plan Exists

Recommendation 7 is about making the configuration match reality. The current `MCTSConfig`
communicates capabilities that the implementation does not actually provide.

## Current Behavior

[`src/chesag/agents/mcts/agent.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/mcts/agent.py)
exposes:

- `parallel`
- `num_workers`
- `rollouts_per_leaf`
- `use_pruning`

Of those, only the pruning/cache path is meaningfully wired. The others suggest capabilities that
are not part of the real search loop.

## What Is Wrong With That

This is not only a code cleanliness issue. It is a search-engine issue:

- callers may believe the agent is parallel when it is not
- tuning experiments may use knobs that do nothing
- future training/self-play work can be planned against a false interface

That creates bad data, not just bad aesthetics.

## Proposed Solution

Pick one of these approaches:

1. Implement the advertised features properly.
1. Remove or deprecate the unsupported options until they are real.

The second option is usually better first. An honest small API is better than a large misleading one.

## Expected Gains

- clearer benchmarks
- more trustworthy tuning
- simpler agent construction and debugging

## Implementation Plan

1. Audit every `MCTSConfig` field and document whether it is live, partially live, or dead.
1. Remove or deprecate dead options in code and docs.
1. If any field remains, add tests that prove it affects behavior.
1. Update CLI exposure if any MCTS flags are surfaced there.
1. Add explicit follow-up tasks for features intentionally deferred.

## Validation

- config-focused tests proving each kept field changes search behavior or output
- documentation review to ensure no dead capability is still advertised

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

- removing config fields can break external scripts if the repo has unpublished local users
- keeping them without implementation is worse for long-term correctness
