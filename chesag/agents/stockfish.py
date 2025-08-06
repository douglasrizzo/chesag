import contextlib

import chess
import chess.engine

from chesag.agents import BaseAgent


class StockfishAgent(BaseAgent):
  """A chess agent that uses the Stockfish engine to make moves."""

  def __init__(self, stockfish_path: str = "/usr/bin/stockfish", time_limit: float = 0.1) -> None:
    """
    Initialize the Stockfish agent with a UCI engine connection.

    Parameters
    ----------
    stockfish_path : str, default="/usr/bin/stockfish"
        Path to the Stockfish executable.
    time_limit : float, default=0.1
        Default time limit in seconds for move calculations.
    """
    self.time_limit = time_limit
    self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)

  def get_move(self, board: chess.Board, time_limit: float | None = None) -> chess.Move:
    """
    Get the best move from Stockfish for the given board position.

    Parameters
    ----------
    board : chess.Board
        The current chess board position.
    time_limit : float or None, optional
        Optional time limit override. If None, uses the instance's default time_limit.

    Returns
    -------
    chess.Move
        The best move according to Stockfish.
    """
    result = self.engine.play(board, chess.engine.Limit(time=time_limit or self.time_limit))
    return result.move

  def close(self):
    with contextlib.suppress(chess.engine.EngineTerminatedError):
      self.engine.quit()
