from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import numpy as np

from chesag.evaluation import material_balance, symmetric_evaluation
from chesag.logging import get_logger
from chesag.move_priority import HeuristicMovePrioritizer

if TYPE_CHECKING:
  from chess import Board, Move

logger = get_logger()


class Node:
  """A node in the Monte Carlo Tree Search tree."""

  def __init__(self, parent: Node | None = None, move: Move | None = None, board: Board | None = None) -> None:
    """Initialize a new node."""
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
      msg = "Either parent or board must be provided"
      raise ValueError(msg)

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
    """Calculate the action value of this node."""
    if self.visits == 0:
      msg = "Node has not been visited yet, cannot get action value"
      raise ValueError(msg)
    return self.value / self.visits

  def expand(self) -> None:
    """Expand the node by creating child nodes using progressive widening."""
    if self.is_terminal():
      return

    # If the node has no available moves to expand, generate them from the list of
    # available moves and order them according to the move prioritizer strategy
    if not self.available_moves:
      self.available_moves = self.move_prioritizer.order_moves(self.board, list(self.board.legal_moves))

    # If this node has not yet been fully expanded, create a minimum number of child nodes
    # from a subset of the available moves, ordered by some prioritization strategy
    if not self.is_expanded:
      initial_moves = self._get_initial_moves()
      for move in initial_moves:
        child = Node(parent=self, move=move)
        self.children.append(child)
        self.available_moves.remove(move)
      # Mark this node as expanded once all moves available in this board position have been evaluated
      if len(self.available_moves) == 0:
        self.is_expanded = True
    else:
      # After this node has been expanded one or more times,
      max_children = min(len(self.available_moves) + len(self.children), max(4, int(math.sqrt(self.visits))))

      while len(self.children) < max_children and self.available_moves:
        move = self.available_moves.pop(0)
        child = Node(parent=self, move=move)
        self.children.append(child)

      if not self.available_moves:
        self.is_expanded = True

  def _get_initial_moves(self) -> list[Move]:
    """Get the initial set of moves to expand."""
    if not self.available_moves:
      return []
    initial_count = min(4, len(self.available_moves)) if len(self.available_moves) > 8 else len(self.available_moves)
    return self.available_moves[:initial_count]

  def select_child(self, c_puct: float) -> Node:
    """Select the best child node using UCB1 formula."""
    if not self.children:
      msg = "Cannot select child from node with no children"
      raise ValueError(msg)

    for child in self.children:
      if child.visits == 0:
        return child

    best_score = float("-inf")
    best_child = None

    for child in self.children:
      exploitation = child.value / child.visits
      exploration = c_puct * math.sqrt(math.log(self.visits) / child.visits)
      score = exploitation + exploration

      if score > best_score:
        best_score = score
        best_child = child

    if best_child is None:
      msg = "No valid child found"
      raise ValueError(msg)
    return best_child

  def rollout(self) -> float:
    """Perform a smarter rollout with early termination and move filtering."""
    rollout_board = self.board.copy()
    moves_played = 0
    max_rollout_moves = 100

    while not rollout_board.is_game_over() and moves_played < max_rollout_moves:
      legal_moves = list(rollout_board.legal_moves)
      if not legal_moves:
        break
      move = self._select_rollout_move(rollout_board, legal_moves)
      rollout_board.push(move)
      moves_played += 1

      if self._should_terminate_rollout(rollout_board):
        break
    return symmetric_evaluation(rollout_board)

  def _select_rollout_move(self, board: Board, legal_moves: list[Move]) -> Move:
    """Select a move for rollout using simple heuristics."""
    # Get move evaluations from the move prioritizer
    move_weights = np.array(self.move_prioritizer.move_evaluations(board, legal_moves))

    # If all weights are the same, select a move randomly
    if np.all(move_weights == move_weights[0]):
      return random.choice(legal_moves)

    # If any of the weights is infinite (checkmate), return that move
    infty_mask = np.isinf(move_weights)
    if infty_mask.any():
      return legal_moves[infty_mask.argmax()]

    # Make sure they are not negative
    if move_weights.min() < 0:
      move_weights -= move_weights.min()
    # Normalize weights to sum to 1
    normalized_move_weights = move_weights / move_weights.sum()
    # Select a move randomly based on the distribution of move evaluations
    return random.choices(legal_moves, weights=normalized_move_weights, k=1)[0]

  def _should_terminate_rollout(self, board: Board) -> bool:
    """Check if rollout should terminate early due to clear advantage."""
    return abs(material_balance(board)) >= 9

  def backpropagate(self, result: float) -> None:
    """Backpropagate the simulation result up the tree."""
    node = self
    while node is not None:
      node.visits += 1
      node.value += result
      result = -result
      node = node.parent
