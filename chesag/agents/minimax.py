import chess
from chess import Board, Move

from chesag.agents.base import BaseAgent
from chesag.evaluation import evaluate, quick_evaluate  # using our improved evaluator
from chesag.logging import MORE_INFO, get_logger
from chesag.move_priority import HeuristicMovePrioritizer

logger = get_logger()


class MinimaxAgent(BaseAgent):
  def __init__(self, maxdepth: int = 4, resign_threshold: float = 6):
    self.move_prioritizer = HeuristicMovePrioritizer()
    self.maxdepth = maxdepth
    self.resign_threshold = resign_threshold
    self.last_search: dict[str, dict[str, int]] = {}

  def get_move(self, board: Board) -> Move:
    # Resign if losing badly from the current side's perspective
    if evaluate(board, board.turn) < -self.resign_threshold:
      return Move.null()

    """Return the best move for the current side."""
    legal_moves = list(board.generate_legal_moves())
    if len(legal_moves) == 1:
      logger.log(MORE_INFO, "Returning single legal move")
      return legal_moves[0]

    sorted_moves = self.move_prioritizer.order_moves(board, legal_moves)
    self.last_search = {"depth_0": {"searched": len(sorted_moves), "pruned": 0}}
    best_move = None
    best_value = float("-inf") if board.turn == chess.WHITE else float("inf")
    maximizing = board.turn == chess.WHITE
    for move in sorted_moves:
      board.push(move)
      value = self.negamax(board, self.maxdepth - 1, float("-inf"), float("inf"), not maximizing)
      board.pop()

      if (maximizing and value > best_value) or (not maximizing and value < best_value):
        best_value = value
        best_move = move

    logger.log(MORE_INFO, "Search results: %s", self.last_search)
    return best_move or sorted_moves[0]

  def negamax(self, board: Board, depth: int, alpha: float, beta: float, maximizing_color: bool) -> float:
    """Alpha-beta search with perspective-aware evaluation."""
    if depth == 0 or board.is_game_over():
      # Switch perspective to the root player: maximizing_color=True means root player is on move
      perspective = chess.WHITE if maximizing_color else chess.BLACK
      return self.quiescence(board, alpha, beta, perspective)

    depth_dict = self.last_search[f"depth_{self.maxdepth - depth}"] = self.last_search.get(
      f"depth_{self.maxdepth - depth}", {"searched": 0, "pruned": 0}
    )
    moves = self.move_prioritizer.order_moves(board, board.generate_legal_moves())
    value = float("-inf")
    for idx, move in enumerate(moves):
      board.push(move)
      value = max(value, -self.negamax(board, depth - 1, -beta, -alpha, not maximizing_color))
      board.pop()
      depth_dict["searched"] += 1
      alpha = max(alpha, value)
      if alpha >= beta:
        self.move_prioritizer.record_history(move, depth)
        depth_dict["pruned"] += len(moves) - idx + 1
        break
    return value

  # --- Quiescence Search ---
  def quiescence(self, board: Board, alpha: float, beta: float, perspective_color: bool) -> float:
    """Extend search on tactical positions to avoid horizon effect."""
    stand_pat = quick_evaluate(board, perspective_color)
    if stand_pat >= beta:
      return beta
    alpha = max(stand_pat, alpha)

    # Only explore noisy moves: captures and promotions
    noisy_moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]
    noisy_moves = self.move_prioritizer.order_moves(board, noisy_moves)

    for move in noisy_moves:
      board.push(move)
      score = -self.quiescence(board, -beta, -alpha, not perspective_color)
      board.pop()

      if score >= beta:
        return beta
      alpha = max(score, alpha)

    return alpha

  def __str__(self):
    return f"MinimaxAgent({self.move_prioritizer}, maxdepth={self.maxdepth})"
