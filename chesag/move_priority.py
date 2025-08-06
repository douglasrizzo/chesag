from abc import ABC, abstractmethod

import chess
from chess import Board, Move


class MovePrioritizer(ABC):
  @abstractmethod
  def evaluate_move(self, move: Move, board: Board) -> float:
    pass

  def order_moves(self, board: Board, moves: list[Move]) -> list[Move]:
    return sorted(moves, key=lambda move: self.evaluate_move(move, board), reverse=True)


class NullMovePrioritizer(MovePrioritizer):
  def evaluate_move(self, move: Move, board: Board) -> float:
    return 0.0

  def order_moves(self, board: Board, moves: list[Move]) -> list[Move]:
    return moves


class HeuristicMovePrioritizer(MovePrioritizer):
  """A move prioritizer that uses chess heuristics to evaluate and order moves."""

  def evaluate_move(self, move: Move, board: Board) -> float:
    """Evaluate a move based on chess heuristics and return a priority score.

    Parameters
    ----------
    move : Move
        The chess move to evaluate
    board : Board
        The current board position

    Returns
    -------
    float
        A float representing the move's priority (higher values = better move)
    """
    priority = 0
    temp_board = board.copy()
    temp_board.push(move)

    if board.is_capture(move):
      captured_piece = board.piece_at(move.to_square)
      if captured_piece:
        priority += 1000 + captured_piece.piece_type * 10

    if temp_board.is_check():
      priority += 500

    if move.promotion:
      priority += 400 + (move.promotion * 10)

    if board.is_castling(move):
      priority += 300

    center_squares = {chess.E4, chess.E5, chess.D4, chess.D5}
    if move.to_square in center_squares:
      priority += 50

    if temp_board.is_attacked_by(not board.turn, move.to_square):
      priority -= 100

    temp_board.pop()
    return priority
