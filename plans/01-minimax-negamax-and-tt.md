# Plan 01: Minimax Perspective Fix And Transposition Table

## Why This Plan Exists

This plan combines two recommendations because they should be implemented together:

1. Make the minimax search theoretically correct.
1. Add a transposition table so alpha-beta can realize its expected performance gains.

If the perspective logic remains unclear, caching will preserve and amplify bad search values.
If caching is added before the sign conventions are settled, debugging becomes much harder.

## Current Behavior

[`src/chesag/agents/minimax.py`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/minimax.py)
currently mixes two different search formulations:

- In [`get_move()`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/minimax.py#L24),
  the root compares values as if White should maximize and Black should minimize.
- In [`negamax()`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/minimax.py#L51),
  the recursion already uses the negamax pattern `-search(child)` with flipped windows.
- At the leaf, evaluation perspective is reconstructed from a toggled boolean at
  [`#L55`](/Users/douglas.meneghetti/code/personal/chesag/src/chesag/agents/minimax.py#L55),
  rather than being defined once from the root side.

In practice, the agent returns legal moves and does not obviously crash, but the code does not
make a strong theoretical guarantee that the returned root score is always from one stable point
of view.

## What Is Wrong With That

Negamax works because one invariant stays true:

- every returned score is from the same player's perspective, usually the root player

The current implementation weakens that invariant in two places:

- the root compares values differently depending on which color is to move
- the leaf evaluation perspective is inferred from an alternating boolean instead of an explicit
  root identity

That introduces three concrete risks:

1. Black-side searches can select moves as if they are minimizing a score that was already
   sign-normalized for Black.
1. A future refactor to quiescence or leaf evaluation can silently break search without changing
   test legality.
1. Alpha-beta pruning can become less trustworthy if scores are not consistently comparable.

## What The Correct Model Should Be

The clean version is:

- capture `root_color = board.turn` once in `get_move()`
- every score returned by search is “good for `root_color`”
- the root always selects the maximum score
- recursive calls flip sign because the opponent's best score is the negative of ours
- quiescence also preserves that same invariant

That gives a single mental model:

- `+score` means good for the root player
- `-score` means good for the opponent

## Why Add A Transposition Table Here

Alpha-beta performance depends heavily on:

- move ordering
- iterative deepening
- transposition reuse

Chess positions repeat by transposition constantly. Without a transposition table, the minimax
agent recomputes identical subtrees from scratch. That wastes most of the work done at deeper
plies and makes future search upgrades less valuable than they should be.

## Proposed Solution

### Part A: Rewrite Minimax As A Clean Negamax

- replace the `maximizing` / `maximizing_color` toggling with an explicit root perspective
- make `get_move()` always choose the highest returned value
- pass a `color_sign` or `root_color` invariant through `negamax()` and `quiescence()`
- make quiescence obey the same convention as the full search
- review alpha-beta window handling after the rewrite

Two acceptable formulations:

1. Root-color formulation
   - keep `root_color`
   - evaluate leaves from `root_color`
   - flip sign on recursion
1. Color-multiplier formulation
   - pass `color = +1/-1`
   - leaf returns `color * evaluate(board, board.turn or root perspective equivalent)`

The repo will be easier to maintain with the root-color formulation because the evaluation
function already accepts a perspective color.

### Part B: Add A Proper Transposition Table

Store entries keyed by position with at least:

- depth searched
- score
- bound type: exact, lower bound, upper bound
- best move if available

This allows:

- exact reuse when the stored node is deep enough
- tighter alpha-beta windows
- better move ordering via TT move first

## Expected Gains

### Correctness Gains

- minimax scores become theoretically interpretable
- Black/White symmetry becomes much easier to test
- quiescence stops being a hidden sign-convention trap

### Performance Gains

- repeated positions will no longer be recomputed
- deeper search becomes feasible for the same time budget
- move ordering quality improves when the TT move is tried first

This is one of the highest-impact changes in the entire engine because it addresses both
correctness and speed.

## Implementation Plan

1. Add targeted tests before changing behavior:
   - symmetric position tests where swapping colors should negate scores
   - root-choice tests on tactical positions for both White and Black
   - quiescence sign-consistency tests
1. Refactor `get_move()` to define a single root perspective and always maximize.
1. Refactor `negamax()` to return scores only in root perspective.
1. Refactor `quiescence()` to follow the same score convention.
1. Add a transposition-table entry type and lookup/store logic.
1. Use the TT best move as the first candidate in move ordering.
1. Add instrumentation so search stats can report TT hits and cutoffs.
1. Run smoke matches against the current implementation to compare node counts and move quality.

## Validation

- `uv run pytest` with dedicated minimax perspective tests
- small fixed-position search assertions for both colors
- node-count comparison before and after TT on the same search depth
- smoke runs such as `uv run chesag play minimax --player2 random --games 2`

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

- it is easy to fix the root while leaving quiescence inconsistent
- TT entries are dangerous if depth and bound type are stored incorrectly
- changing multiple sign conventions at once can create “looks plausible” bugs

That is why this plan should be implemented before broader search tuning.
