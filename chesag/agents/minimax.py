from typing import Literal

from chess import Board, Move

from chesag.agents.base import BaseAgent
from chesag.evaluation import material_balance
from chesag.move_priority import HeuristicMovePrioritizer


class MinimaxAgent(BaseAgent):
  def __init__(self, maxdepth: int = 5, resign_threshold: float = 6):
    self.move_prioritizer = HeuristicMovePrioritizer()
    self.maxdepth = maxdepth
    self.resign_threshold = resign_threshold

  def get_move(self, board: Board, maxdepth: int | None = None) -> Move:
    if material_balance(board) > self.resign_threshold:
      return Move.null()
    return self.minimax(board, maxdepth or self.maxdepth)

  def alphabeta_step(self, board: Board, depth: int, sign: Literal[-1, 1], alpha: float, beta: float) -> float:
    if board.is_game_over():
      return self.move_prioritizer.evaluate_board(board)
    if depth == 0:
      return self.move_prioritizer.evaluate_board(board)
    score = float("inf") * sign
    moves = self.move_prioritizer.order_moves(board, list(board.generate_legal_moves()))
    for move in moves:
      board.push(move)
      score = max(score, self.alphabeta_step(board, depth - 1, -sign, alpha, beta))
      board.pop()
      if sign == -1 and score >= alpha:
        alpha = score
      elif sign == 1 and score <= beta:
        beta = score
      if alpha >= beta:
        break
    return score

  def minimax(self, board: Board, depth: int) -> Move:
    legal_moves = list(board.generate_legal_moves())
    if len(legal_moves) == 1:
      return legal_moves[0]

    sorted_moves = self.move_prioritizer.order_moves(board, legal_moves)

    best_move = None
    best_value = float("-inf")
    for move in sorted_moves:
      board.push(move)
      value = self.alphabeta_step(board, depth - 1, -1, float("-inf"), float("inf"))
      board.pop()
      if value > best_value:
        best_value = value
        best_move = move
    return best_move

  def __str__(self):
    return f"MinimaxAgent({self.move_prioritizer}, maxdepth={self.maxdepth})"
