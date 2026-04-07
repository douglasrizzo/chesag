# Master Plan

## Objective

Bring `chesag` to a safe, theoretically correct, and well-structured state:

1. Fix the confirmed correctness and performance issues in the search stack.
2. Ensure every phase lands with tests and a clean quality gate.
3. Close with a deliberate review and refactor pass.

## Current State Summary

- Tooling, tests, packaging, and quality gates are in place (phases 01–04 completed).
- The package is small and navigable, with clear separation between game loop, agents,
  evaluation, viewer, and reporting.
- The remaining work is concentrated in the search stack, where correctness conventions and
  performance costs interact.

## Confirmed Findings Driving The Remaining Plan

- Minimax perspective handling is not theoretically consistent; the current code mixes
  max/min root selection with a negamax recursive body.
- MCTS selection and expansion do not form a clean UCT or PUCT policy.
- Move ordering calls the full evaluator on every interior node, paying leaf-evaluation cost
  at ordering time.
- The evaluator has no explicit cost tiers; high-frequency search paths use the same expensive
  function as leaf evaluation.
- Some MCTS configuration fields advertise capabilities that are not wired.
- MCTS uses `board.fen()` as a cache key; a cheaper integer hash would reduce overhead.

## Implementation Order

1. [`01-minimax-negamax-and-tt.md`](01-minimax-negamax-and-tt.md)
1. [`02-evaluation-tiers.md`](02-evaluation-tiers.md)
1. [`03-cheap-move-ordering.md`](03-cheap-move-ordering.md)
1. [`04-ordering-state-reuse.md`](04-ordering-state-reuse.md)
1. [`05-mcts-tree-policy.md`](05-mcts-tree-policy.md)
1. [`06-mcts-config-honesty.md`](06-mcts-config-honesty.md)
1. [`07-mcts-position-keying.md`](07-mcts-position-keying.md)
1. [`08-review-and-refactor.md`](08-review-and-refactor.md)

The ordering is deliberate:

- Minimax correctness (01) must land before any caching or tuning work.
- Evaluation tiers (02) and cheap ordering (03, 04) reduce overhead before MCTS tuning.
- MCTS tree policy (05) is easier to reason about once evaluation cost is explicit.
- Config honesty (06) and keying (07) are lower-risk cleanup that follows from cleaner search.
- The final review (08) consolidates all changes into a coherent codebase.

## After Each Plan

Every plan must finish with:

1. Tests written or updated for all changed behavior.
2. Full quality gate run in order:
   - `uv run ruff check --fix`
   - `uv run ruff format`
   - `uv run ruff check`
   - `uv run ty check`
   - `uv run pytest`
3. All checks passing cleanly before moving to the next plan.

## Package Areas To Prioritize During Implementation

- [`src/chesag/agents/minimax.py`](../src/chesag/agents/minimax.py)
- [`src/chesag/agents/mcts/agent.py`](../src/chesag/agents/mcts/agent.py)
- [`src/chesag/agents/mcts/algorithm.py`](../src/chesag/agents/mcts/algorithm.py)
- [`src/chesag/agents/mcts/node.py`](../src/chesag/agents/mcts/node.py)
- [`src/chesag/evaluation.py`](../src/chesag/evaluation.py)
- [`src/chesag/move_priority.py`](../src/chesag/move_priority.py)
- [`src/chesag/game/game.py`](../src/chesag/game/game.py)
- [`src/chesag/game/results.py`](../src/chesag/game/results.py)
- [`src/chesag/game/statistics.py`](../src/chesag/game/statistics.py)
- [`src/chesag/replay.py`](../src/chesag/replay.py)
- [`src/chesag/cli.py`](../src/chesag/cli.py)

## Validation Strategy

- Keep smoke tests small and local.
- Prefer deterministic tests where possible.
- For search agents, validate legality first, then specific behavioral contracts.
- Do not change multiple high-risk search/evaluation conventions at once without tests landing first.
