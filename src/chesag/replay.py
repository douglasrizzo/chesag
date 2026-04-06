"""PGN replay support."""

import time
from pathlib import Path

import chess.pgn

from chesag.viewer import ChessViewer


def replay(pgn_file: str, move_delay: float) -> None:
  """Replay a PGN game in the viewer."""
  with Path(pgn_file).open(encoding="utf-8") as f:
    game = chess.pgn.read_game(f)
    if game is None:
      msg = f"No PGN game found in {pgn_file}"
      raise ValueError(msg)

    viewer = ChessViewer()
    white_name = game.headers["White"]
    black_name = game.headers["Black"]
    viewer.initialize()
    board = game.board()
    viewer.update_board(board, white_name, black_name)
    for move in game.mainline_moves():
      board.push(move)
      viewer.update_board(board, white_name, black_name)
      time.sleep(move_delay)
