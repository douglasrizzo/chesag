from abc import ABC, abstractmethod

from chess import Board, Move


class BaseAgent(ABC):
  """Abstract base class for chess agents."""

  @abstractmethod
  def get_move(self, board: Board) -> Move:
    """Generate a move for the given board position.

    Parameters
    ----------
    board : Board
        The current chess board position.

    Returns
    -------
    Move
        A Move object representing the agent's chosen move.
    """

  def close(self):
    pass

  def __str__(self) -> str:
    """Return a string representation of the agent."""
    return self.__class__.__name__

  def __repr__(self) -> str:
    """Return a detailed string representation of the agent."""
    return f"{self.__class__.__name__}()"
