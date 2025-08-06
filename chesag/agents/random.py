from chess import Board, Move
from numpy.random import default_rng

from chesag.agents import BaseAgent


class RandomAgent(BaseAgent):
  """A chess agent that selects moves randomly from all legal moves.

  This agent uses a random number generator to choose uniformly at random
  from the set of legal moves available in any given position.
  """

  def __init__(self, seed: int | None = None) -> None:
    """Initialize the RandomAgent.

    Parameters
    ----------
    seed : int or None, optional
        Seed for the random number generator. If None, the generator
        will be initialized with a random seed.
    """
    self.generator = default_rng(seed)

  def get_move(self, board: Board) -> Move:
    """Select a random legal move from the current board position.

    Parameters
    ----------
    board : Board
        The current chess board position.

    Returns
    -------
    Move
        A randomly selected legal move from the current position.
    """
    legal_moves = list(board.legal_moves)
    return self.generator.choice(legal_moves)
