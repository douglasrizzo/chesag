"""Core MCTS search algorithm."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cachetools import LRUCache

from chesag.agents.mcts.node import Node
from chesag.evaluation import leaf_evaluate
from chesag.logging import get_logger
from chesag.move_priority import HeuristicMovePrioritizer
from chesag.position_key import build_position_key

if TYPE_CHECKING:
  from collections.abc import Hashable

  from chess import Board, Move

logger = get_logger()


@dataclass
class CachedNode:
  """Cached node data for transposition table."""

  value: float
  visits: int
  best_move: Move | None = None

  @property
  def score(self) -> float:
    """Return the average cached score."""
    return self.value / self.visits if self.visits > 0 else 0.0


class MCTSSearcher:
  """Core MCTS search functionality."""

  cache_file = Path("cache/mcts_cache_v2.pickle")

  def __init__(self, use_transposition_table: bool = True) -> None:
    """Initialize the searcher and optional transposition table."""
    self.cache_persist_interval = 1000
    self.remaining_simulations_until_cache_persist = self.cache_persist_interval
    self.move_prioritizer = HeuristicMovePrioritizer()
    self.transposition_table = self.load_cache() if use_transposition_table else None

  @staticmethod
  def load_cache() -> LRUCache[Hashable, CachedNode]:
    """Load the persisted transposition table if present."""
    if not MCTSSearcher.cache_file.exists():
      logger.info("Cache file not found, creating new cache")
      return LRUCache(maxsize=500_000)
    try:
      with MCTSSearcher.cache_file.open("rb") as f:
        cache: LRUCache[Hashable, CachedNode] = pickle.load(f)
      logger.info("Loaded transposition table with %d entries", len(cache))
      return cache
    except Exception:
      logger.warning("Cache file could not be loaded; starting with a fresh table")
      return LRUCache(maxsize=500_000)

  def save_cache(self) -> None:
    """Persist the transposition table to disk."""
    if self.transposition_table is not None:
      self.cache_file.parent.mkdir(parents=True, exist_ok=True)
      with self.cache_file.open("wb") as f:
        pickle.dump(self.transposition_table, f)
        logger.log(18, "Saved transposition table (%d entries)", len(self.transposition_table))

  @staticmethod
  def get_legal_moves(board: Board) -> list[Move]:
    """Return legal moves for a non-terminal board."""
    if board.is_game_over():
      raise ValueError("Cannot search from terminal position")
    legal_moves = list(board.legal_moves)
    if not legal_moves:
      raise ValueError("No legal moves available")
    return legal_moves

  @staticmethod
  def should_return_single_move(board: Board) -> tuple[Move, float] | None:
    """Short-circuit positions with exactly one legal move."""
    legal_moves = MCTSSearcher.get_legal_moves(board)
    if len(legal_moves) == 1:
      next_board = board.copy()
      next_board.push(legal_moves[0])
      logger.debug("Single move found: %s", legal_moves[0])
      return legal_moves[0], leaf_evaluate(next_board, board.turn)
    return None

  @staticmethod
  def position_key(board: Board) -> Hashable:
    """Return a compact transposition key for a chess position."""
    return build_position_key(board)

  def _lookup_tt_entry(self, board: Board) -> CachedNode | None:
    if self.transposition_table is None:
      return None
    return self.transposition_table.get(self.position_key(board))

  def create_root_node(self, board: Board) -> Node:
    """Create and expand the root search node."""
    root = Node(board=board.copy(), move_prioritizer=self.move_prioritizer)
    logger.debug("Creating root node")
    if root.expand() is None:
      raise ValueError("Failed to expand root node")
    return root

  def single_step(self, root: Node, c_puct: float) -> float:
    """Run one MCTS simulation from the root."""
    current = root

    while not current.is_terminal() and current.children and not current.can_expand():
      current = current.select_child(c_puct)

    if not current.is_terminal():
      tt_entry = self._lookup_tt_entry(current.board)
      expanded_child = current.expand(tt_move=tt_entry.best_move if tt_entry is not None else None)
      if expanded_child is not None:
        current = expanded_child

    result = self.simulate(current)
    current.backpropagate(result)
    return result

  def simulate(self, node: Node) -> float:
    """Evaluate one node by rollout or cached value."""
    if node.is_terminal():
      return leaf_evaluate(node.board, node.board.turn)

    position_key = self.position_key(node.board)

    if self.transposition_table is not None:
      cached = self.transposition_table.get(position_key)
      if cached is not None and cached.visits >= 200:
        return cached.score

    result = node.rollout()

    if self.transposition_table is not None:
      if position_key not in self.transposition_table:
        self.transposition_table[position_key] = CachedNode(result, 1, node.move)
      else:
        entry = self.transposition_table[position_key]
        entry.value += result
        entry.visits += 1
        if entry.best_move is None:
          entry.best_move = node.move

    return result

  def search(self, root: Node, num_simulations: int, c_puct: float) -> None:
    """Run repeated MCTS simulations from the root."""
    for sim in range(num_simulations):
      logger.debug("Sim %s/%s", sim + 1, num_simulations)
      if self.transposition_table is not None:
        self.remaining_simulations_until_cache_persist -= 1
        logger.debug("Remaining simulations until cache persist: %s", self.remaining_simulations_until_cache_persist)
      self.single_step(root, c_puct)

    if self.transposition_table is not None and self.remaining_simulations_until_cache_persist <= 0:
      self.save_cache()
      self.remaining_simulations_until_cache_persist = self.cache_persist_interval

  @staticmethod
  def get_best_child(root: Node) -> tuple[Move, int, float]:
    """Select the best root child using visit count then value."""
    visited_children = [child for child in root.children if child.visits > 0]
    candidate_children = visited_children or root.children
    best_child = max(candidate_children, key=lambda child: (child.visits, -child.action_value))
    if best_child is None or best_child.move is None:
      raise ValueError("No best move found")
    return best_child.move, best_child.visits, best_child.value

  @staticmethod
  def aggregate_results(results: list[tuple[str, int, float]]) -> dict[str, float]:
    """Aggregate worker results into average move values."""
    move_visits: dict[str, int] = {}
    move_values: dict[str, float] = {}
    for move_uci, visits, values in results:
      if move_uci and visits > 0:
        move_visits[move_uci] = move_visits.get(move_uci, 0) + visits
        move_values[move_uci] = move_values.get(move_uci, 0.0) + values
    return {move_uci: move_values[move_uci] / move_visits[move_uci] for move_uci in move_visits}
