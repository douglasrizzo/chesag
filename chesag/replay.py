import time
from pathlib import Path

import chess.pgn

from chesag.viewer import ChessViewer


def replay(pgn_file: str, move_delay: float):
  with Path(pgn_file).open(encoding="utf-8") as f:
    game = chess.pgn.read_game(f)
    viewer = ChessViewer(game.headers["Event"])
    white_name = game.headers["White"]
    black_name = game.headers["Black"]
    viewer.initialize()
    board = game.board()
    viewer.update_board(board, white_name, black_name)
    for move in game.mainline_moves():
      board.push(move)
      viewer.update_board(board, white_name, black_name)
      time.sleep(move_delay)
