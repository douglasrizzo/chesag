"""Move ordering heuristics."""

import operator
from collections import defaultdict

from chess import Board, Move

from chesag.evaluation import evaluate, quick_evaluate


class HeuristicMovePrioritizer:
  """Score and order moves for search algorithms."""

  def __init__(self) -> None:
    """Initialize move-ordering state."""
    self.killer_moves = defaultdict(list)  # depth -> [Move, Move]
    self.history_heuristic = defaultdict(int)  # move key -> score

  def evaluate_move(self, move: Move, board: Board) -> float:
    """Full board evaluation from the perspective of side to move."""
    board.push(move)
    score = evaluate(board, perspective_color=not board.turn, include_move_bonus=True)
    board.pop()
    return score

  def order_moves(self, board: Board, moves: list[Move]) -> list[Move]:
    """Order moves using quick heuristics first, then evaluation as tiebreaker."""
    move_scores = []
    for move in moves:
      board.push(move)
      try:
        quick = quick_evaluate(board, perspective_color=not board.turn)
        full = evaluate(board, perspective_color=not board.turn, include_move_bonus=True)
      finally:
        board.pop()
      move_scores.append((quick, full, move))

    move_scores.sort(key=operator.itemgetter(0, 1), reverse=True)
    return [move for _, _, move in move_scores]

  def record_history(self, move: Move, depth: int) -> None:
    """Increment history heuristic score for a move."""
    self.history_heuristic[move.from_square, move.to_square] += depth * depth

  def __str__(self) -> str:
    """Return the prioritizer name."""
    return self.__class__.__name__
