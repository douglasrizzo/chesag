import chess

from chesag.position_key import build_position_key


def test_position_key_matches_for_identical_positions() -> None:
  board1 = chess.Board()
  board2 = chess.Board()

  assert build_position_key(board1) == build_position_key(board2)


def test_position_key_distinguishes_side_to_move() -> None:
  board_white = chess.Board()
  board_black = chess.Board()
  board_black.push_san("e4")
  board_black.pop()
  board_black.turn = chess.BLACK

  assert build_position_key(board_white) != build_position_key(board_black)


def test_position_key_distinguishes_castling_rights() -> None:
  board_with_rights = chess.Board()
  board_without_rights = chess.Board()
  board_without_rights.castling_rights = 0

  assert build_position_key(board_with_rights) != build_position_key(board_without_rights)


def test_position_key_distinguishes_en_passant_state() -> None:
  board_without_ep = chess.Board()
  board_with_ep = chess.Board()
  board_with_ep.push_san("e4")

  assert build_position_key(board_without_ep) != build_position_key(board_with_ep)
