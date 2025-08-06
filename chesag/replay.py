import time
from pathlib import Path

import chess.pgn

from chesag.chess import ExtendedBoard
from chesag.viewer import ChessViewer


def replay(pgn_file: str, move_delay: float):
  with Path(pgn_file).open(encoding="utf-8") as f:
    game = chess.pgn.read_game(f)
    viewer = ChessViewer(game.headers["Event"])
    viewer.initialize()
    board = ExtendedBoard(game.board().fen())
    viewer.update_board(board)
    for move in game.mainline_moves():
      board.push(move)
      viewer.update_board(board)
      time.sleep(move_delay)
