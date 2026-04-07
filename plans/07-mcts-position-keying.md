# Plan 07: Improve MCTS Position Keying And Cache Reuse

## Why This Plan Exists

Recommendation 8 is to replace the current heavy position keying approach with something cheaper
and more search-oriented.

## Current Behavior

[`simulate()` in `algorithm.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/mcts/algorithm.py#L118)
uses `board.fen()` as the transposition-table key.

That is easy to understand, but it has drawbacks:

- string allocation cost
- larger memory footprint
- repeated serialization overhead in a hot path

## What Is Wrong With That

The cache exists to make search cheaper. If key creation itself is expensive, some of the benefit
is lost before lookup even happens.

FEN is also broader than what a search cache strictly wants to optimize for. It is a great debug
format, but not the most efficient runtime key.

## Proposed Solution

Move to a more compact and purpose-built key:

- preferably a chess position hash exposed by `python-chess`, if suitable
- otherwise a custom compact tuple capturing the state dimensions that affect legality/evaluation

Requirements:

- identical positions must map to the same key
- keys must distinguish turn, castling rights, and en passant state where relevant
- the key must be stable enough for persisted caches if persistence is kept

## Expected Gains

- cheaper cache lookups
- smaller cache entries
- better scaling when simulations increase

This is not the first thing to do, but it becomes worthwhile once the main search loops are cleaner.

## Implementation Plan

1. Inspect what stable hashing support `python-chess` already exposes.
1. Compare at least two candidate key strategies for speed and correctness.
1. Refactor cache access behind a dedicated key builder.
1. Add tests for key equality and inequality on positions differing by:
   - side to move
   - castling rights
   - en passant availability
1. Re-evaluate whether persisted caches should survive key-format changes.

## Validation

- unit tests for key correctness
- simulation benchmark comparing cache lookup overhead before and after

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

- incorrect keying causes silent transposition corruption
- persisted cache files may need versioning or invalidation
