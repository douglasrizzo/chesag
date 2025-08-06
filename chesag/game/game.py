import time

import chess
from tqdm import tqdm

from chesag.agents import BaseAgent
from chesag.chess import ExtendedBoard
from chesag.game.results import GameResult
from chesag.viewer import ChessViewer


class Game:
  """Represents a single game between two agents."""

  def __init__(
    self,
    player1_agent: BaseAgent,
    player2_agent: BaseAgent,
    player1_is_white: bool,
    fen: str | None = None,
    viewer: ChessViewer | None = None,
    move_delay: float = 0.0,
  ) -> None:
    """Initialize a new game between two agents."""
    self.board = ExtendedBoard(fen=fen or chess.STARTING_FEN)
    self.moves = 0
    self.start_time = time.time()
    self.move_delay = move_delay

    self.viewer = viewer

    # Determine which agent plays which color
    self.player1_is_white = player1_is_white
    self.white_agent = player1_agent if player1_is_white else player2_agent
    self.black_agent = player2_agent if player1_is_white else player1_agent

  def play(self, game_num: int | None = None) -> GameResult:
    """Play a single game between two agents and return the result."""
    if game_num is None:
      game_num = 1

    # Initialize viewer if provided
    if self.viewer is not None:
      self.viewer.update_board(self.board)
      time.sleep(self.move_delay)

    # Create progress bar for this game
    game_desc = f"Game {game_num}"
    pbar = tqdm(unit=" halfmoves", desc=game_desc, leave=False)

    start_time = time.time()
    side_to_move = self.board.turn
    outcome = None
    while outcome is None:
      self.make_move(side_to_move)
      side_to_move = not side_to_move
      pbar.update(1)
      outcome = self.board.extended_outcome()
    pbar.close()
    duration = time.time() - start_time
    termination_reason = outcome.termination.name

    return GameResult(
      result=outcome.result(),
      moves=self.board.fullmove_number,
      duration=duration,
      player1_agent=str(self.white_agent if self.player1_is_white else self.black_agent),
      player2_agent=str(self.black_agent if self.player1_is_white else self.white_agent),
      player1_color="white" if self.player1_is_white else "black",
      player2_color="black" if self.player1_is_white else "white",
      termination_reason=termination_reason,
    )

  def make_move(self, color: chess.Color):
    move = self.white_agent.get_move(self.board) if color == chess.WHITE else self.black_agent.get_move(self.board)
    self.board.push(move)

    # Update viewer after black's move
    if self.viewer is not None:
      self.viewer.update_board(self.board)
      time.sleep(self.move_delay)
