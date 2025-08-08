from abc import ABC, abstractmethod

from chess import Board, Move

from chesag.evaluation import heuristic_evaluation


class MovePrioritizer(ABC):
  def evaluate_move(self, move: Move, board: Board) -> float:
    board.push(move)
    priority = self.evaluate_board(board)
    board.pop()
    return priority

  @abstractmethod
  def evaluate_board(self, board: Board) -> float:
    msg = "Subclasses must implement evaluate_board"
    raise NotImplementedError(msg)

  def order_moves(self, board: Board, moves: list[Move]) -> list[Move]:
    return sorted(moves, key=lambda move: self.evaluate_move(move, board), reverse=True)

  def move_evaluations(self, board: Board, moves: list[Move]) -> list[float]:
    return [self.evaluate_move(move, board) for move in moves]


class HeuristicMovePrioritizer(MovePrioritizer):
  """A move prioritizer that uses chess heuristics to evaluate and order moves."""

  def evaluate_board(self, board: Board) -> float:
    """Evaluate a board based on chess heuristics and return a priority score.

    Parameters
    ----------
    board : Board
        The current board position

    Returns
    -------
    float
        A float representing the move's priority (higher values = better move)
    """
    return heuristic_evaluation(board)

  def __str__(self) -> str:
    return self.__class__.__name__
