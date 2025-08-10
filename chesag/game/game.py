import time

import chess
from chess import Board, Move
from tqdm import tqdm

from chesag.agents import BaseAgent
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
    self.board = Board(fen=fen or chess.STARTING_FEN)
    self.moves = 0
    self.start_time = time.time()
    self.move_delay = move_delay
    self.viewer = viewer

    # Color assignments
    self.player1_is_white = player1_is_white
    self.white_agent = player1_agent if player1_is_white else player2_agent
    self.black_agent = player2_agent if player1_is_white else player1_agent

    # Cached agent string representations for consistent display
    self.white_agent_str = str(self.white_agent)
    self.black_agent_str = str(self.black_agent)

  def play(self, game_num: int | None = None) -> GameResult:
    """Play a single game between two agents and return the result."""
    if game_num is None:
      game_num = 1

    # Initial board display
    if self.viewer is not None:
      self.viewer.update_board(self.board, self.white_agent_str, self.black_agent_str)
      time.sleep(self.move_delay)

    pbar = tqdm(unit="ply", desc=f"Game {game_num}", leave=False)

    start_time = time.time()
    side_to_move = self.board.turn
    outcome = None
    resigned = False

    while outcome is None and not resigned:
      move = self.make_move(side_to_move)
      resigned = not bool(move)  # True if Move.null()
      if resigned:
        resigning_color = side_to_move
        break

      pbar.update(1)
      outcome = self.board.outcome()
      side_to_move = not side_to_move

    pbar.close()
    duration = time.time() - start_time

    if resigned:
      result = "0-1" if resigning_color == chess.WHITE else "1-0"
      termination_reason = "RESIGNATION"
      winner_agent = self.black_agent if resigning_color == chess.WHITE else self.white_agent
      if hasattr(winner_agent, "win_by_resignation"):
        winner_agent.win_by_resignation(self.board)
    else:
      result = outcome.result()
      termination_reason = outcome.termination.name

    return GameResult(
      result=result,
      moves=self.board.fullmove_number,
      duration=duration,
      player1_agent=str(self.white_agent if self.player1_is_white else self.black_agent),
      player2_agent=str(self.black_agent if self.player1_is_white else self.white_agent),
      player1_color="white" if self.player1_is_white else "black",
      player2_color="black" if self.player1_is_white else "white",
      termination_reason=termination_reason,
    )

  def make_move(self, color: chess.Color) -> Move:
    """Request the given color's agent to make a move and update the board."""
    agent = self.white_agent if color == chess.WHITE else self.black_agent
    move = agent.get_move(self.board)
    self.board.push(move)

    if self.viewer is not None:
      self.viewer.update_board(self.board, self.white_agent_str, self.black_agent_str)
      time.sleep(self.move_delay)

    return move
