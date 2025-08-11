from __future__ import annotations

import pickle
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cachetools import LRUCache

from chesag.agents.mcts.node import Node
from chesag.evaluation import evaluate
from chesag.logging import get_logger

if TYPE_CHECKING:
  from chess import Board, Move

  from chesag.agents.mcts.move_selection import MoveSelectionStrategy

logger = get_logger()


@dataclass
class CachedNode:
  """Cached node data for transposition table."""

  value: float  # cumulative score
  visits: int

  @property
  def score(self) -> float:
    return self.value / self.visits if self.visits > 0 else 0.0


class MCTSSearcher:
  """Core MCTS search functionality."""

  cache_file = Path("cache/mcts_cache.pickle")

  def __init__(self, move_selection: MoveSelectionStrategy, use_pruning: bool = True):
    self.move_selector = move_selection.value
    self.cache_persist_interval = 1000
    self.remaining_simulations_until_cache_persist = self.cache_persist_interval
    self.transposition_table = self.load_cache() if use_pruning else None

  @staticmethod
  def load_cache() -> LRUCache[str, CachedNode]:
    if not MCTSSearcher.cache_file.exists():
      logger.info("Cache file not found, creating new cache")
      return LRUCache(maxsize=500_000)
    with MCTSSearcher.cache_file.open("rb") as f:
      cache: LRUCache[str, CachedNode] = pickle.load(f)
      logger.info("Loaded transposition table with %d entries", len(cache))
      return cache

  def save_cache(self):
    if self.transposition_table is not None:
      with self.cache_file.open("wb") as f:
        pickle.dump(self.transposition_table, f)
        logger.log(18, "Saved transposition table (%d entries)", len(self.transposition_table))

  @staticmethod
  def get_legal_moves(board: Board) -> list[Move]:
    if board.is_game_over():
      raise ValueError("Cannot search from terminal position")
    legal_moves = list(board.legal_moves)
    if not legal_moves:
      raise ValueError("No legal moves available")
    return legal_moves

  @staticmethod
  def should_return_single_move(board: Board) -> tuple[Move, float] | None:
    legal_moves = MCTSSearcher.get_legal_moves(board)
    if len(legal_moves) == 1:
      next_board = board.copy()
      next_board.push(legal_moves[0])
      logger.debug("Single move found: %s", legal_moves[0])
      return legal_moves[0], evaluate(next_board, board.turn)
    return None

  def create_root_node(self, board: Board) -> Node:
    root = Node(board=board.copy())
    logger.debug("Creating root node")
    root.expand()
    if not root.children:
      raise ValueError("Failed to expand root node")
    return root

  def single_step(self, root: Node, c_puct: float) -> float:
    """Run one MCTS simulation from the root."""
    path = [root]
    current = root
    perspective_color = current.board.turn

    # Selection
    while not current.is_terminal() and current.is_expanded and current.children:
      current = current.select_child(c_puct)
      path.append(current)

    # Expansion
    if not current.is_terminal():
      if not current.is_expanded or not current.children:
        current.expand()
      if current.children:
        current = random.choice(current.children)
        path.append(current)

    # Simulation
    result = self.simulate(current, perspective_color)

    # Backpropagation
    current.backpropagate(result)
    return result

  def simulate(self, node: Node, perspective_color: bool) -> float:
    if node.is_terminal():
      return evaluate(node.board, perspective_color=node.board.turn)  # STM perspective

    fen = node.board.fen()

    # If we have a cache entry, return it, flipping sign if needed
    if self.transposition_table is not None:
      cached = self.transposition_table.get(fen)
      if cached and cached.visits >= 200:
        # Flip sign if the caller's perspective differs from STM
        return cached.value if perspective_color == node.board.turn else -cached.value

    # Run rollout from the STM perspective
    result = node.rollout()

    # Normalize result to STM perspective before storing
    normalized_result = result if perspective_color == node.board.turn else -result

    if self.transposition_table is not None:
      if fen not in self.transposition_table:
        self.transposition_table[fen] = CachedNode(normalized_result, 1)
      else:
        entry = self.transposition_table[fen]
        entry.value += normalized_result
        entry.visits += 1

    return result

  def search(self, root: Node, num_simulations: int, c_puct: float) -> None:
    for sim in range(num_simulations):
      logger.debug("Sim %s/%s", sim + 1, num_simulations)
      if self.transposition_table is not None:
        self.remaining_simulations_until_cache_persist -= 1
        logger.debug("Remaining simulations until cache persist: %s", self.remaining_simulations_until_cache_persist)
      self.single_step(root, c_puct)

    if self.transposition_table is not None and self.remaining_simulations_until_cache_persist <= 0:
      self.save_cache()
      self.remaining_simulations_until_cache_persist = self.cache_persist_interval

  def get_best_child(self, root: Node) -> tuple[Move, int, float]:
    best_child = self.move_selector.select_best_child(root)
    if best_child is None or best_child.move is None:
      raise ValueError("No best move found")
    return best_child.move, best_child.visits, best_child.value

  def aggregate_results(self, results: list[tuple[str, int, float]]) -> dict[str, int]:
    return self.move_selector.aggregate_results(results)
