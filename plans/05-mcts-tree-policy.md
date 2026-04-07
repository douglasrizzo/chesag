# Plan 05: MCTS Tree Policy And Expansion Semantics

## Why This Plan Exists

The current MCTS code runs, but its selection and expansion phases do not form a clean,
consistent tree policy. That hurts both theory and playing strength.

This plan is focused on recommendation 2:

- simplify MCTS into a coherent UCT or PUCT implementation

## Current Behavior

[`src/chesag/agents/mcts/node.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/mcts/node.py)
and [`src/chesag/agents/mcts/algorithm.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/mcts/algorithm.py)
currently do the following:

- `select_child()` immediately returns the first unvisited child
- visited children are scored with an exploitation term plus a pseudo-prior derived from static
  evaluation
- after expansion, `single_step()` picks a random child from the entire child list

There is also progressive widening in `expand()`, which is a valid idea in isolation, but it is
currently combined with the behaviors above in a way that makes the effective policy hard to
describe precisely.

## What Is Wrong With That

MCTS works best when each simulation follows one clear contract:

1. Selection follows a single scoring rule.
1. Expansion adds one or more children under a known policy.
1. Simulation or leaf evaluation starts from the newly selected child.
1. Backpropagation updates values with a well-defined perspective convention.

The current implementation breaks that conceptual cleanliness:

- returning the first unvisited child introduces move-list bias
- choosing a random child after expansion throws away the work done by the selection policy
- using on-demand evaluator scores as “priors” is not wrong in a heuristic sense, but it is not
  true PUCT unless those priors are stable policy estimates associated with the node

So the main issue is not that the code is nonsense. The issue is that the code is using several
partially compatible ideas at once.

## Recommended Direction

Choose one of these and implement it cleanly:

1. Pure UCT
   - no prior term
   - score children with average value plus exploration bonus
   - simpler and easier to debug
1. Heuristic PUCT
   - compute a prior once at expansion time
   - store it on the child
   - use that stored prior in selection

For this repo, heuristic PUCT is a good fit because the code already wants evaluation-guided
selection, but it must be implemented consistently.

## Proposed Solution

- during expansion, create one new child at a time or a deliberately bounded batch
- assign each new child a stored prior when it is created
- in selection, evaluate all candidates with the same formula every time
- remove the “first unvisited child” shortcut
- after expansion, continue the simulation from the newly added child rather than a random one

If progressive widening is kept, define it clearly:

- when a node reaches a visit threshold, add the next best child by prior
- selection only happens among existing children

That yields a tree policy that can actually be described and tuned.

## Expected Gains

- less move-order bias
- more reliable search statistics
- better use of limited simulations
- easier debugging because each phase of MCTS has a crisp role

This is likely to improve playing strength even before deeper evaluator work lands.

## Implementation Plan

1. Add tests for selection behavior:
   - unvisited-child selection should not depend on list order alone
   - expansion should return a deterministic newly-added child under controlled conditions
1. Decide on final policy shape: UCT or heuristic PUCT.
1. Add a stored prior field to child nodes if using PUCT.
1. Rewrite `expand()` so expansion semantics are explicit.
1. Rewrite `single_step()` so simulation starts from the selected/expanded child, not a random one.
1. Re-check backpropagation sign handling after the tree-policy rewrite.
1. Profile simulation counts and win rates against random/minimax baselines.

## Validation

- deterministic unit tests on small artificial trees
- smoke games with fixed simulation counts
- instrumentation for root visit distribution before and after the rewrite

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

- keeping progressive widening without clear thresholds can make the policy hard to reason about
- cached values and selection logic must still agree on perspective
