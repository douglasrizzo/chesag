import chess

from chesag.agents.base import BaseAgent
from chesag.game import Game


class ScriptedAgent(BaseAgent):
  def __init__(self, moves: list[str]) -> None:
    self.moves = list(moves)

  def get_move(self, board: chess.Board) -> chess.Move:
    _ = board
    move = self.moves.pop(0)
    return chess.Move.from_uci(move)


class ResigningAgent(BaseAgent):
  def get_move(self, board: chess.Board) -> chess.Move:
    _ = board
    return chess.Move.null()


def test_game_reports_checkmate_result() -> None:
  white = ScriptedAgent(["f2f3", "g2g4"])
  black = ScriptedAgent(["e7e5", "d8h4"])
  game = Game(white, black, player1_is_white=True)

  result = game.play()

  assert result.result == "0-1"
  assert result.termination_reason == "CHECKMATE"
  assert result.player1_color == "white"
  assert result.player2_color == "black"
  assert game.board.is_checkmate()


def test_game_tracks_player_perspective_when_colors_swap() -> None:
  black_as_player1 = ScriptedAgent(["e7e5", "d8h4"])
  white_as_player2 = ScriptedAgent(["f2f3", "g2g4"])
  game = Game(black_as_player1, white_as_player2, player1_is_white=False)

  result = game.play()

  assert result.result == "0-1"
  assert result.player1_color == "black"
  assert result.player2_color == "white"
  assert result.player1_result == "1-0"
  assert result.player2_result == "0-1"


def test_resignation_does_not_mutate_board_state() -> None:
  game = Game(ResigningAgent(), ScriptedAgent(["e2e4"]), player1_is_white=True)

  result = game.play()

  assert result.termination_reason == "RESIGNATION"
  assert len(game.board.move_stack) == 0
  assert game.board.turn == chess.WHITE
