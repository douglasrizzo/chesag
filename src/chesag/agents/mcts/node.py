"""MCTS tree node implementation."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import numpy as np

from chesag.evaluation import leaf_evaluate, rollout_evaluate
from chesag.move_priority import HeuristicMovePrioritizer

if TYPE_CHECKING:
  from chess import Board, Move


class Node:
  """A node in the Monte Carlo Tree Search tree."""

  def __init__(
    self,
    *,
    parent: Node | None = None,
    move: Move | None = None,
    board: Board | None = None,
    move_prioritizer: HeuristicMovePrioritizer | None = None,
    prior: float = 0.0,
  ) -> None:
    """Initialize a node from either a parent/move pair or a board copy."""
    assert parent is not None or board is not None, "Either parent or board must be provided"
    self.parent = parent
    self.move = move
    self.move_prioritizer = move_prioritizer or HeuristicMovePrioritizer()
    self.prior = prior

    if board is not None:
      self.board = board.copy()
    elif parent is not None:
      self.board = parent.board.copy()
      if move is not None:
        self.board.push(move)
    else:
      raise ValueError("Either parent or board must be provided")

    self.children: list[Node] = []
    self.visits = 0
    self.value = 0.0
    self._ordered_moves: list[Move] | None = None

  @property
  def depth(self) -> int:
    """Return the node depth from the root."""
    if self.parent is None:
      return 0
    return self.parent.depth + 1

  @property
  def is_expanded(self) -> bool:
    """Return whether this node has created any children."""
    return bool(self.children)

  @property
  def is_fully_expanded(self) -> bool:
    """Return whether all legal moves have been turned into children."""
    return self._ordered_moves is not None and not self._ordered_moves

  def can_expand(self) -> bool:
    """Return whether the node may add another child under widening limits."""
    if self._ordered_moves is None:
      return True
    return bool(self._ordered_moves) and len(self.children) < self._expansion_limit()

  def _expansion_limit(self) -> int:
    """Return the widening limit for this node based on current visits."""
    return max(1, int(math.sqrt(self.visits + 1)))

  @property
  def action_value(self) -> float:
    """Return the average value accumulated at this node."""
    if self.visits == 0:
      return 0.0
    return self.value / self.visits

  def is_terminal(self) -> bool:
    """Check if this node represents a terminal game state."""
    return self.board.is_game_over()

  def expand(self, *, tt_move: Move | None = None) -> Node | None:
    """Expand exactly one ordered child and return it."""
    if self.is_terminal():
      return None
    if self._ordered_moves is None:
      legal_moves = list(self.board.legal_moves)
      self._ordered_moves = self.move_prioritizer.order_moves(
        self.board,
        legal_moves,
        depth=self.depth,
        tt_move=tt_move,
      )
    if not self._ordered_moves:
      return None
    if len(self.children) >= self._expansion_limit():
      return None

    move = self._ordered_moves.pop(0)
    child = Node(
      parent=self,
      move=move,
      move_prioritizer=self.move_prioritizer,
      prior=self._move_prior(move),
    )
    self.children.append(child)
    return child

  def select_child(self, c_puct: float) -> Node:
    """Select a child using one consistent PUCT formula."""
    if not self.children:
      raise ValueError("Cannot select child from node with no children")

    parent_scale = math.sqrt(max(self.visits, 1))
    return max(
      self.children,
      key=lambda child: -child.action_value + (c_puct * child.prior * parent_scale / (1 + child.visits)),
    )

  def rollout(self) -> float:
    """Play a light rollout from the node and return the score for the node side to move."""
    rollout_board = self.board.copy()
    perspective_color = rollout_board.turn
    max_rollout_moves = 24

    for _ in range(max_rollout_moves):
      if rollout_board.is_game_over():
        break
      legal_moves = list(rollout_board.legal_moves)
      if not legal_moves:
        break

      move = self._select_rollout_move(rollout_board, legal_moves)
      rollout_board.push(move)

      eval_score = rollout_evaluate(rollout_board, perspective_color)
      if abs(eval_score) >= 8.0:
        break

    return leaf_evaluate(rollout_board, perspective_color)

  def _select_rollout_move(self, board: Board, legal_moves: list[Move]) -> Move:
    weights = []
    mover = board.turn
    for move in legal_moves:
      board.push(move)
      try:
        weights.append(rollout_evaluate(board, mover))
      finally:
        board.pop()

    move_weights = np.array(weights, dtype=float)
    if np.isinf(move_weights).any():
      return legal_moves[int(np.isinf(move_weights).argmax())]
    if np.allclose(move_weights, move_weights[0]):
      return random.choice(legal_moves)
    if move_weights.min() <= 0:
      move_weights = move_weights - move_weights.min() + 1e-6

    normalized_weights = move_weights / move_weights.sum()
    return random.choices(legal_moves, weights=normalized_weights.tolist(), k=1)[0]

  def backpropagate(self, result: float) -> None:
    """Backpropagate a side-to-move score up the tree, alternating perspective."""
    node: Node | None = self
    score = result
    while node is not None:
      node.visits += 1
      node.value += score
      score = -score
      node = node.parent

  def _move_prior(self, move: Move) -> float:
    """Compute and store a cheap prior for the move at expansion time."""
    mover = self.board.turn
    self.board.push(move)
    try:
      raw_score = rollout_evaluate(self.board, mover)
    finally:
      self.board.pop()
    return 1.0 / (1.0 + math.exp(-raw_score / 2.0))
