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

  def win_by_resignation(self, board: Board) -> None:
    """Signal the agent that it has won by resignation.

    Parameters
    ----------
    board : Board
        The current chess board position.
    """

  def close(self) -> None:
    pass

  def __str__(self) -> str:
    """Return a string representation of the agent."""
    return self.__class__.__name__
