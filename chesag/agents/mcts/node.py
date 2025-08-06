from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from chesag.move_priority import HeuristicMovePrioritizer

if TYPE_CHECKING:
  from chesag.chess import ExtendedBoard
  from chess import Board, Move


class Node:
  """A node in the Monte Carlo Tree Search tree."""

  def __init__(self, parent: Node | None = None, move: Move | None = None, board: ExtendedBoard | None = None) -> None:
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
    return self.board.extended_game_over()

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

    while not rollout_board.extended_game_over() and moves_played < max_rollout_moves:
      legal_moves = list(rollout_board.legal_moves)
      if not legal_moves:
        break

      move = self._select_rollout_move(rollout_board, legal_moves)
      rollout_board.push(move)
      moves_played += 1

      if self._should_terminate_rollout(rollout_board):
        break
    return rollout_board.evaluation()

  def _select_rollout_move(self, board: Board, legal_moves: list[Move]) -> Move:
    """Select a move for rollout using simple heuristics."""
    captures = []
    checks = []

    for move in legal_moves:
      temp_board = board.copy()
      temp_board.push(move)

      if board.is_capture(move):
        captures.append(move)
      elif temp_board.is_check():
        checks.append(move)

    if captures and random.random() < 0.6:
      return random.choice(captures)
    if checks and random.random() < 0.3:
      return random.choice(checks)
    return random.choice(legal_moves)

  def _should_terminate_rollout(self, board: ExtendedBoard) -> bool:
    """Check if rollout should terminate early due to clear advantage."""
    material_balance = board.material_balance()
    return abs(material_balance) >= 9

  def backpropagate(self, result: float) -> None:
    """Backpropagate the simulation result up the tree."""
    node = self
    while node is not None:
      node.visits += 1
      node.value += result
      result = -result
      node = node.parent
