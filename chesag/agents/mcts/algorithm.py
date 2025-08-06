from __future__ import annotations

import pickle
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cachetools import LRUCache
from chesag.agents.mcts.node import Node
from chesag.logging import get_logger

if TYPE_CHECKING:
  from chesag.agents.mcts.move_selection import MoveSelectionStrategy
  from chesag.chess import ExtendedBoard
  from chess import Board, Move

logger = get_logger()


@dataclass
class CachedNode:
  """Cached node data for transposition table."""

  value: float
  visits: int

  @property
  def score(self) -> float:
    """Calculate the score of the node."""
    return self.value / self.visits


class MCTSSearcher:
  """Core MCTS search functionality shared across different strategies."""

  cache_file = Path("cache/mcts_cache.pickle")

  def __init__(self, move_selection: MoveSelectionStrategy, use_pruning: bool = True):
    self.move_selector = move_selection.value
    self.cache_persist_interval = 1000
    self.remaining_simulations_until_cache_persist = self.cache_persist_interval
    if use_pruning:
      MCTSSearcher.cache_file.parent.mkdir(parents=True, exist_ok=True)
      self.transposition_table = self.load_cache()
    else:
      self.transposition_table = None

  @staticmethod
  def load_cache() -> LRUCache[str, CachedNode]:
    if not MCTSSearcher.cache_file.exists():
      logger.info("Cache file not found, creating new cache")
      return LRUCache(maxsize=20000)
    with MCTSSearcher.cache_file.open("rb") as f:
      cache: LRUCache[str, CachedNode] = pickle.load(f)
      logger.info("Cached transposition table loaded from file %s with %d entries", MCTSSearcher.cache_file, len(cache))
      return cache

  def save_cache(self):
    with MCTSSearcher.cache_file.open("wb") as f:
      if self.transposition_table is not None:
        pickle.dump(self.transposition_table, f)
        logger.info(
          "Cached transposition table saved to file %s (%d entries)",
          MCTSSearcher.cache_file,
          len(self.transposition_table),
        )

  @staticmethod
  def get_legal_moves(board: Board) -> list[Move]:
    """Validate search parameters and return legal moves."""
    if board.is_game_over():
      msg = "Cannot search from terminal position"
      raise ValueError(msg)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
      msg = "No legal moves available"
      raise ValueError(msg)

    return legal_moves

  @staticmethod
  def should_return_single_move(board: ExtendedBoard) -> tuple[Move, float] | None:
    """Return move immediately if only one legal move exists."""
    legal_moves = MCTSSearcher.get_legal_moves(board)

    # If there is a single legal move, return it alongside its value
    if len(legal_moves) == 1:
      next_board = board.copy()
      next_board.push(legal_moves[0])
      logger.debug("Single move found: %s", legal_moves[0])
      return legal_moves[0], next_board.evaluation()

    # If there are multiple legal moves, return None
    return None

  def create_root_node(self, board: ExtendedBoard) -> Node:
    """Create and initialize root node."""
    root = Node(board=board.copy())
    logger.debug("Creating root node")
    root.expand()

    if not root.children:
      msg = "Failed to expand root node"
      raise ValueError(msg)

    return root

  def single_step(self, root: Node, c_puct: float) -> float:
    """Execute a single MCTS step."""
    logger.debug("Executing simulation")

    # Selection phase
    logger.debug("Selection phase")
    path = [root]
    current = root

    # Traverse down a path as long as the current node is not terminal, has been expanded, and has children
    while not current.is_terminal() and current.is_expanded and current.children:
      logger.debug("Selecting child")
      # Node selection combines exploration and exploitation
      # New paths are eventually explored, giving preference to most promising ones
      current = current.select_child(c_puct)
      path.append(current)

    # Expansion phase
    logger.debug("Expansion phase")
    # At this step, we have reached a non-expanded node (its subtree hasn't been explored yet)
    if not current.is_terminal():
      logger.debug("Expanding non-terminal node")

      # Generate children for the current node, following some strategy.
      # If the node was never expanded or has no children (children are removed after exploration), expand it.
      # Not all strategies fully expand the node, so calling expand() again on the same node may generate more unexplored
      # children.
      if not current.is_expanded or not current.children:
        current.expand()
      # If the node has children (regardless of whether expansion was performed), choose a random one
      if current.children:
        current = random.choice(current.children)
        path.append(current)

    # Simulation phase
    logger.debug("Simulation phase")
    result = self.simulate(current)

    # Backpropagation phase
    logger.debug("Backpropagation phase")
    current.backpropagate(result)
    return result

  def simulate(self, node: Node) -> float:
    """Get simulation result, using cache if available."""
    # Terminal nodes do not require simulation and have their value returned
    if node.is_terminal():
      logger.debug("Evaluating terminal node")
      return node.board.evaluation()

    fen = node.board.fen()

    # If using cache and the number of visits for the given node is greater than or equal to a predetermined value
    if self.transposition_table is not None:
      cached = self.transposition_table.get(fen)
      if not cached:
        logger.debug("No cached result found for current node")
      elif cached.visits < 200:
        logger.debug("Cached result has been visited %s times, needs more simulations", cached.visits)
      else:
        logger.debug("Using cached result")
        return cached.value

    # Perform rollout on the node
    result = node.rollout()
    logger.debug("Rollout result: %s", result)
    # If using cache, add the node, its result, and its visits to the cache
    if self.transposition_table is not None:
      self.transposition_table[fen] = CachedNode(result, 1)
      if len(self.transposition_table) % 1000 == 0:
        logger.debug("Transposition table size: %s", len(self.transposition_table))

    return result

  def search(self, root: Node, num_simulations: int, c_puct: float) -> None:
    """Run MCTS simulations from the root node."""
    for sim in range(num_simulations):
      if self.transposition_table is not None:
        logger.log(
          15,
          "Sim %s/%s (%s for cache persist)",
          sim + 1,
          num_simulations,
          self.remaining_simulations_until_cache_persist,
        )
        self.remaining_simulations_until_cache_persist -= 1
      else:
        logger.info("Sim %s/%s", sim + 1, num_simulations)

      self.single_step(root, c_puct)

    if self.transposition_table is not None and self.remaining_simulations_until_cache_persist <= 0:
      self.save_cache()
      self.remaining_simulations_until_cache_persist = self.cache_persist_interval

  def get_best_child(self, root: Node) -> tuple[Move, int, float]:
    """Get the best move from the root node."""
    best_child = self.move_selector.select_best_child(root)
    if best_child is None or best_child.move is None:
      msg = "No best move found"
      raise ValueError(msg)
    return best_child.move, best_child.visits, best_child.value

  def aggregate_results(self, results: list[tuple[str, int, float]]) -> dict[str, int]:
    """Aggregate the results of MCTS simulations, useful when search is parallelized."""
    return self.move_selector.aggregate_results(results)
