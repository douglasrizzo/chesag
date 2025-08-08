from chess import Board, Move
from numpy.random import default_rng

from chesag.agents import BaseAgent
from chesag.evaluation import material_balance


class RandomAgent(BaseAgent):
  """A chess agent that selects moves randomly from all legal moves.

  This agent uses a random number generator to choose uniformly at random
  from the set of legal moves available in any given position.
  """

  def __init__(self, seed: int | None = None, resign_threshold: float = 6) -> None:
    """Initialize the RandomAgent.

    Parameters
    ----------
    seed : int or None, optional
        Seed for the random number generator. If None, the generator
        will be initialized with a random seed.
    resign_threshold : float, optional
        The threshold for resigning. If the agent's score is below this
        threshold, it will resign.
    """
    self.generator = default_rng(seed)
    self.resign_threshold = resign_threshold

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
    if material_balance(board) > self.resign_threshold:
      return Move.null()
    legal_moves = list(board.legal_moves)
    return self.generator.choice(legal_moves)
