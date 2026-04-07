"""Move ordering heuristics."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from chesag.evaluation import PIECE_VALUES, mvv_lva_score, order_evaluate

if TYPE_CHECKING:
  from chess import Board, Move

TT_MOVE_BONUS = 1_000_000.0
PROMOTION_BONUS = 50_000.0
CAPTURE_BONUS = 10_000.0
CHECK_BONUS = 2_000.0
KILLER_MOVE_BONUS = 1_500.0
HISTORY_SCALE = 0.1
ORDER_TIEBREAK_SCALE = 1.0


class HeuristicMovePrioritizer:
  """Score and order moves for search algorithms."""

  def __init__(self) -> None:
    """Initialize move-ordering state."""
    self.killer_moves: dict[int, list[Move]] = defaultdict(list)
    self.history_heuristic: dict[tuple[int, int, int | None], int] = defaultdict(int)

  def order_moves(
    self,
    board: Board,
    moves: list[Move],
    *,
    depth: int = 0,
    tt_move: Move | None = None,
  ) -> list[Move]:
    """Order moves using cheap tactical and learned heuristics."""
    return sorted(moves, key=lambda move: self.score_move(board, move, depth=depth, tt_move=tt_move), reverse=True)

  def evaluate_move(self, move: Move, board: Board) -> float:
    """Return a cheap static score for a single move."""
    board.push(move)
    try:
      return order_evaluate(board, not board.turn)
    finally:
      board.pop()

  def score_move(self, board: Board, move: Move, *, depth: int = 0, tt_move: Move | None = None) -> float:
    """Return a composite move-ordering score."""
    if tt_move is not None and move == tt_move:
      return TT_MOVE_BONUS

    score = 0.0
    is_capture = board.is_capture(move)
    promotion = move.promotion

    if promotion is not None:
      promoted_piece = PIECE_VALUES[promotion]
      score += PROMOTION_BONUS + promoted_piece
    if is_capture:
      score += CAPTURE_BONUS + mvv_lva_score(board, move)
    if board.gives_check(move):
      score += CHECK_BONUS

    if not is_capture and promotion is None:
      if move in self.killer_moves[depth]:
        score += KILLER_MOVE_BONUS
      score += self.history_heuristic[self._history_key(move)] * HISTORY_SCALE

    board.push(move)
    try:
      score += ORDER_TIEBREAK_SCALE * order_evaluate(board, not board.turn)
    finally:
      board.pop()
    return score

  def record_history(self, move: Move, depth: int) -> None:
    """Increment history heuristic score for a move that caused a cutoff."""
    self.history_heuristic[self._history_key(move)] += max(1, depth) * max(1, depth)

  def record_killer(self, move: Move, depth: int) -> None:
    """Remember up to two quiet cutoff moves per ply."""
    killers = self.killer_moves[depth]
    if move in killers:
      killers.remove(move)
    killers.insert(0, move)
    del killers[2:]

  @staticmethod
  def _history_key(move: Move) -> tuple[int, int, int | None]:
    return move.from_square, move.to_square, move.promotion

  def __str__(self) -> str:
    """Return the prioritizer name."""
    return self.__class__.__name__
