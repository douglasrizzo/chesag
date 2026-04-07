"""Minimax-based chess agent with alpha-beta pruning and a transposition table."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from chess import Board, Move

from chesag.agents.base import BaseAgent
from chesag.evaluation import leaf_evaluate
from chesag.logging import MORE_INFO, get_logger
from chesag.move_priority import HeuristicMovePrioritizer
from chesag.position_key import PositionKey, build_position_key

logger = get_logger()


class Bound(Enum):
  """Bound type stored in the transposition table."""

  EXACT = auto()
  LOWER = auto()
  UPPER = auto()


@dataclass(slots=True)
class TTEntry:
  """Transposition-table entry."""

  depth: int
  score: float
  bound: Bound
  best_move: Move | None


@dataclass(slots=True)
class DepthStats:
  """Per-ply search statistics."""

  searched: int = 0
  pruned: int = 0


@dataclass(slots=True)
class SearchStats:
  """Minimax search instrumentation."""

  tt_hits: int = 0
  tt_cutoffs: int = 0
  depths: dict[int, DepthStats] = field(default_factory=dict)

  def depth(self, ply: int) -> DepthStats:
    """Return per-ply stats, creating them on first use."""
    return self.depths.setdefault(ply, DepthStats())

  def as_dict(self) -> dict[str, int | dict[str, dict[str, int]]]:
    """Return a stable dict view for logging and tests."""
    return {
      "tt_hits": self.tt_hits,
      "tt_cutoffs": self.tt_cutoffs,
      "depths": {
        f"depth_{ply}": {"searched": stats.searched, "pruned": stats.pruned}
        for ply, stats in sorted(self.depths.items())
      },
    }


class MinimaxAgent(BaseAgent):
  """Depth-limited alpha-beta negamax agent with transposition reuse."""

  def __init__(self, maxdepth: int = 4, resign_threshold: float | None = None) -> None:
    """Initialize the minimax agent."""
    self.move_prioritizer = HeuristicMovePrioritizer()
    self.maxdepth = maxdepth
    self.resign_threshold = min(resign_threshold, -resign_threshold) if resign_threshold is not None else float("-inf")
    self.last_search = SearchStats()
    self._tt: dict[PositionKey, TTEntry] = {}

  def get_move(self, board: Board) -> Move:
    """Return the best move for the current side."""
    if leaf_evaluate(board, board.turn) < self.resign_threshold:
      return Move.null()

    legal_moves = list(board.generate_legal_moves())
    if len(legal_moves) == 1:
      logger.log(MORE_INFO, "Returning single legal move")
      return legal_moves[0]

    self.last_search = SearchStats()
    root_key = build_position_key(board)
    tt_entry = self._tt.get(root_key)
    tt_move = tt_entry.best_move if tt_entry is not None else None
    ordered_moves = self.move_prioritizer.order_moves(board, legal_moves, depth=0, tt_move=tt_move)

    best_move = ordered_moves[0]
    best_value = float("-inf")
    alpha = float("-inf")
    beta = float("inf")

    for move in ordered_moves:
      board.push(move)
      try:
        value = -self._negamax(board, self.maxdepth - 1, -beta, -alpha, ply=1)
      finally:
        board.pop()
      self.last_search.depth(0).searched += 1
      if value > best_value:
        best_value = value
        best_move = move
      alpha = max(alpha, best_value)

    self._tt[root_key] = TTEntry(depth=self.maxdepth, score=best_value, bound=Bound.EXACT, best_move=best_move)
    logger.log(MORE_INFO, "Search results: %s", self.last_search.as_dict())
    return best_move

  def _negamax(self, board: Board, depth: int, alpha: float, beta: float, *, ply: int) -> float:
    """Return the score from the current side-to-move perspective."""
    key = build_position_key(board)
    original_alpha = alpha
    original_beta = beta
    tt_move = None

    entry = self._tt.get(key)
    if entry is not None and entry.depth >= depth:
      self.last_search.tt_hits += 1
      if entry.bound is Bound.EXACT:
        return entry.score
      if entry.bound is Bound.LOWER:
        alpha = max(alpha, entry.score)
      else:
        beta = min(beta, entry.score)
      if alpha >= beta:
        self.last_search.tt_cutoffs += 1
        return entry.score
      tt_move = entry.best_move

    if depth <= 0 or board.is_game_over():
      return self.quiescence(board, alpha, beta, ply=ply)

    depth_stats = self.last_search.depth(ply)
    legal_moves = list(board.generate_legal_moves())
    ordered_moves = self.move_prioritizer.order_moves(board, legal_moves, depth=ply, tt_move=tt_move)

    best_value = float("-inf")
    best_move = ordered_moves[0]
    for index, move in enumerate(ordered_moves):
      board.push(move)
      try:
        child_value = -self._negamax(board, depth - 1, -beta, -alpha, ply=ply + 1)
      finally:
        board.pop()

      depth_stats.searched += 1
      if child_value > best_value:
        best_value = child_value
        best_move = move
      alpha = max(alpha, best_value)
      if alpha >= beta:
        depth_stats.pruned += len(ordered_moves) - index - 1
        if not board.is_capture(move) and move.promotion is None:
          self.move_prioritizer.record_killer(move, ply)
        self.move_prioritizer.record_history(move, depth)
        break

    if best_value <= original_alpha:
      bound = Bound.UPPER
    elif best_value >= original_beta:
      bound = Bound.LOWER
    else:
      bound = Bound.EXACT
    self._tt[key] = TTEntry(depth=depth, score=best_value, bound=bound, best_move=best_move)
    return best_value

  def quiescence(self, board: Board, alpha: float, beta: float, *, ply: int = 0) -> float:
    """Extend the search across tactical moves to reduce horizon effects."""
    stand_pat = leaf_evaluate(board, board.turn)
    if stand_pat >= beta:
      return stand_pat
    alpha = max(alpha, stand_pat)

    noisy_moves = [move for move in board.legal_moves if board.is_capture(move) or move.promotion is not None]
    ordered_moves = self.move_prioritizer.order_moves(board, noisy_moves, depth=ply)

    for move in ordered_moves:
      board.push(move)
      try:
        score = -self.quiescence(board, -beta, -alpha, ply=ply + 1)
      finally:
        board.pop()
      if score >= beta:
        return score
      alpha = max(alpha, score)
    return alpha

  def __str__(self) -> str:
    """Return a compact agent description."""
    return f"MinimaxAgent({self.move_prioritizer}, maxdepth={self.maxdepth})"
