from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import numpy as np

from chesag.evaluation import evaluate, quick_evaluate
from chesag.logging import get_logger
from chesag.move_priority import HeuristicMovePrioritizer  # improved version with killer/history

if TYPE_CHECKING:
  from chess import Board, Move

logger = get_logger()


class Node:
  """A node in the Monte Carlo Tree Search tree."""

  def __init__(self, parent: Node | None = None, move: Move | None = None, board: Board | None = None) -> None:
    assert parent is not None or board is not None, "Either parent or board must be provided"
    self.parent = parent
    self.move = move

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
    self.is_expanded = False
    self.available_moves: list[Move] = []
    self.move_prioritizer = HeuristicMovePrioritizer()

  def is_terminal(self) -> bool:
    """Check if this node represents a terminal game state."""
    return self.board.is_game_over()

  @property
  def action_value(self) -> float:
    if self.visits == 0:
      raise ValueError("Node has not been visited yet")
    return self.value / self.visits

  def expand(self) -> None:
    """Expand node using progressive widening and move prioritizer."""
    if self.is_terminal():
      return

    if not self.available_moves:
      self.available_moves = self.move_prioritizer.order_moves(self.board, list(self.board.legal_moves))

    if not self.is_expanded:
      initial_moves = self._get_initial_moves()
      for move in initial_moves:
        self.children.append(Node(parent=self, move=move))
        self.available_moves.remove(move)
      if not self.available_moves:
        self.is_expanded = True
    else:
      max_children = min(len(self.available_moves) + len(self.children), max(4, int(math.sqrt(self.visits))))
      while len(self.children) < max_children and self.available_moves:
        move = self.available_moves.pop(0)
        self.children.append(Node(parent=self, move=move))
      if not self.available_moves:
        self.is_expanded = True

  def _get_initial_moves(self) -> list[Move]:
    if not self.available_moves:
      return []
    return (
      self.available_moves[: min(4, len(self.available_moves))]
      if len(self.available_moves) > 8
      else self.available_moves
    )

  def select_child(self, c_puct: float) -> Node:
    """Select child using PUCT formula."""
    if not self.children:
      raise ValueError("Cannot select child from node with no children")

    # Return any unvisited child first
    for child in self.children:
      if child.visits == 0:
        return child

    best_score = float("-inf")
    best_child = None

    for child in self.children:
      exploitation = child.value / child.visits
      raw = self.move_prioritizer.evaluate_move(child.move, self.board)
      # smooth squash
      prior = 1 / (1 + math.exp(-raw / 2.0))  # maps to (0,1)
      exploration = c_puct * prior * math.sqrt(self.visits) / (1 + child.visits)
      score = exploitation + exploration

      if score > best_score:
        best_score = score
        best_child = child

    if best_child is None:
      # Choose randomly from unvisited children, else from all children
      unvisited_children = [child for child in self.children if child.visits == 0]
      best_child = random.choice(unvisited_children) if unvisited_children else random.choice(self.children)
    return best_child

  def rollout(self) -> float:
    """Smarter rollout with early cutoff using heuristic eval."""
    rollout_board = self.board.copy()
    perspective_color = self.board.turn
    moves_played = 0
    max_rollout_moves = 40

    while not rollout_board.is_game_over() and moves_played < max_rollout_moves:
      legal_moves = list(rollout_board.legal_moves)
      if not legal_moves:
        break
      move = self._select_rollout_move(rollout_board, legal_moves, perspective_color)
      rollout_board.push(move)
      moves_played += 1

      eval_score = evaluate(rollout_board, perspective_color, include_move_bonus=True)
      if abs(eval_score) > 8.0:
        break

    return evaluate(rollout_board, perspective_color)

  def _select_rollout_move(self, board: Board, legal_moves: list[Move], perspective_color: bool) -> Move:
    weights = []
    for m in legal_moves:
      board.push(m)
      try:
        w = quick_evaluate(board, perspective_color)
      finally:
        board.pop()
      weights.append(w)
    move_weights = np.array(weights)

    if np.all(move_weights == move_weights[0]):
      return random.choice(legal_moves)

    if np.isinf(move_weights).any():
      return legal_moves[np.isinf(move_weights).argmax()]

    if move_weights.min() < 0:
      move_weights -= move_weights.min()

    normalized_weights = move_weights / move_weights.sum()
    return random.choices(legal_moves, weights=normalized_weights, k=1)[0]

  def backpropagate(self, result: float) -> None:
    """Backpropagate result up the tree, alternating perspective."""
    node = self
    while node is not None:
      node.visits += 1
      node.value += result
      result = -result
      node = node.parent
