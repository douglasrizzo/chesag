from collections.abc import Iterable

import chess
from chess import Board, Move

# --- Piece values ---
PIECE_VALUES = {
  chess.PAWN: 1.0,
  chess.KNIGHT: 3.2,
  chess.BISHOP: 3.33,
  chess.ROOK: 5.1,
  chess.QUEEN: 9.5,
  chess.KING: 0.0,  # King value not used in eval
}

# --- Evaluation Weights ---
BISHOP_PAIR_BONUS = 0.5
PASSED_PAWN_BONUS = 0.2
CENTER_CONTROL_WEIGHT = 0.1
KING_CASTLE_BONUS = 0.25
KING_OPEN_FILE_PENALTY = -0.2
PAWN_SHIELD_PENALTY = -0.1
MOVE_CAPTURE_WEIGHT = 0.1
MOVE_CHECK_BONUS = 0.3

# Central and extended central squares

CENTER4 = (chess.D4, chess.E4, chess.D5, chess.E5)
EXTENDED_CENTER = {
  chess.C3,
  chess.C4,
  chess.C5,
  chess.C6,
  chess.D3,
  chess.D4,
  chess.D5,
  chess.D6,
  chess.E3,
  chess.E4,
  chess.E5,
  chess.E6,
  chess.F3,
  chess.F4,
  chess.F5,
  chess.F6,
}


# --- Main evaluation ---
def evaluate(
  board: Board,
  perspective_color: bool,
  *,
  include_move_bonus: bool = False,
  use_material: bool = True,
  use_bishop_pair: bool = True,
  use_passed_pawns: bool = True,
  use_center_basic: bool = False,
  use_center_extended: bool = True,
  use_king_safety: bool = True,
  use_mobility: bool = True,
) -> float:
  """
  Evaluate board from perspective_color's point of view.
  Positive = good for perspective_color, Negative = good for opponent.

  Toggle components with flags to trade strength for speed.

  Notes
  -----
  - If both `use_center_basic` and `use_center_extended` are True, `use_center_extended` wins
    (to avoid double-counting).
  """
  # Terminal conditions
  if board.is_checkmate():
    return float("inf") if board.turn != perspective_color else -float("inf")
  if board.is_stalemate() or board.is_insufficient_material():
    return 0.0

  score = 0.0

  if use_material:
    score += material_balance(board, perspective_color)
  if use_bishop_pair:
    score += bishop_pair_bonus(board, perspective_color)
  if use_passed_pawns:
    score += passed_pawn_score(board, perspective_color)

  # Center control: prefer extended if both were requested
  if use_center_extended:
    score += center_control(board, perspective_color, EXTENDED_CENTER)
  elif use_center_basic:
    score += center_control(board, perspective_color, CENTER4)

  if use_king_safety:
    score += king_safety(board, perspective_color)
  if use_mobility:
    score += mobility_score(board, perspective_color)

  if include_move_bonus and board.move_stack:
    score += move_bonus(board, perspective_color)

  return score


def quick_evaluate(board: Board, perspective_color: bool) -> float:
  """
  Very fast evaluation (few loops / no heavy queries).
  Good for move ordering or quiescence standing-pat.

  Components:
  - material_balance
  - bishop_pair_bonus
  - center_control_basic (D4/E4/D5/E5)
  (No passed pawns, no king safety scans, no mobility, no move bonus.)
  """
  return evaluate(
    board,
    perspective_color,
    include_move_bonus=False,
    use_material=True,
    use_bishop_pair=True,
    use_passed_pawns=False,
    use_center_basic=True,
    use_center_extended=False,
    use_king_safety=False,
    use_mobility=False,
  )


# --- Feature functions ---
def material_balance(board: Board, perspective_color: bool) -> float:
  score = 0
  for piece_type, value in PIECE_VALUES.items():
    score += value * len(board.pieces(piece_type, chess.WHITE))
    score -= value * len(board.pieces(piece_type, chess.BLACK))
  return score if perspective_color == chess.WHITE else -score


def bishop_pair_bonus(board: Board, perspective_color: bool) -> float:
  score = 0
  if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
    score += BISHOP_PAIR_BONUS
  if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
    score -= BISHOP_PAIR_BONUS
  return score if perspective_color == chess.WHITE else -score


def passed_pawn_score(board: Board, perspective_color: bool) -> float:
  score = 0.0
  for pawn_square in board.pieces(chess.PAWN, chess.WHITE):
    if is_passed_pawn(board, pawn_square, chess.WHITE):
      rank = chess.square_rank(pawn_square)
      score += PASSED_PAWN_BONUS * (rank / 6)
  for pawn_square in board.pieces(chess.PAWN, chess.BLACK):
    if is_passed_pawn(board, pawn_square, chess.BLACK):
      rank = 7 - chess.square_rank(pawn_square)
      score -= PASSED_PAWN_BONUS * (rank / 6)
  return score if perspective_color == chess.WHITE else -score


def is_passed_pawn(board: Board, square: chess.Square, color: bool) -> bool:
  """Check if pawn has no enemy pawns blocking or on adjacent files ahead."""
  file = chess.square_file(square)
  rank = chess.square_rank(square)
  direction = 1 if color == chess.WHITE else -1
  enemy_pawns = board.pieces(chess.PAWN, not color)

  for r in range(rank + direction, 8 if color == chess.WHITE else -1, direction):
    for f in (file - 1, file, file + 1):
      if 0 <= f <= 7 and chess.square(f, r) in enemy_pawns:
        return False
  return True


def center_control(board: Board, perspective_color: bool, squares: Iterable[chess.Square]) -> float:
  w = sum(len(board.attackers(chess.WHITE, sq)) for sq in squares)
  b = sum(len(board.attackers(chess.BLACK, sq)) for sq in squares)
  score = (w - b) * CENTER_CONTROL_WEIGHT
  return score if perspective_color == chess.WHITE else -score


def king_safety(board: Board, perspective_color: bool) -> float:
  score = 0.0
  king_square_white = board.king(chess.WHITE)
  king_square_black = board.king(chess.BLACK)

  # Castling rights
  if board.has_kingside_castling_rights(chess.WHITE):
    score += KING_CASTLE_BONUS
  if board.has_queenside_castling_rights(chess.WHITE):
    score += KING_CASTLE_BONUS
  if board.has_kingside_castling_rights(chess.BLACK):
    score -= KING_CASTLE_BONUS
  if board.has_queenside_castling_rights(chess.BLACK):
    score -= KING_CASTLE_BONUS

  # Open files near king
  if king_square_white is not None:
    score += open_file_and_shield_penalty(board, king_square_white, chess.WHITE)
  if king_square_black is not None:
    score -= open_file_and_shield_penalty(board, king_square_black, chess.BLACK)

  return score if perspective_color == chess.WHITE else -score


def open_file_and_shield_penalty(board: Board, king_square: chess.Square, color: bool) -> float:
  score = 0.0
  king_file = chess.square_file(king_square)

  # Half-open files near king (no friendly pawns on that file)
  for f in (king_file - 1, king_file, king_file + 1):
    if 0 <= f <= 7:
      file_squares = [chess.square(f, r) for r in range(8)]
      if not any(board.piece_type_at(sq) == chess.PAWN and board.color_at(sq) == color for sq in file_squares):
        score += KING_OPEN_FILE_PENALTY

  # Pawn shield one rank in front of the king
  forward = 1 if color == chess.WHITE else -1
  target_rank = chess.square_rank(king_square) + forward
  if 0 <= target_rank <= 7:
    shield_files = [f for f in (king_file - 1, king_file, king_file + 1) if 0 <= f <= 7]
    shield_squares = [chess.square(f, target_rank) for f in shield_files]
    for sq in shield_squares:
      if board.piece_type_at(sq) != chess.PAWN or board.color_at(sq) != color:
        score += PAWN_SHIELD_PENALTY

  return score


def mobility_score(board: Board, perspective_color: bool) -> float:
  # Save current turn
  saved_turn = board.turn

  # White mobility
  board.turn = chess.WHITE
  mobility_white = sum(1 for _ in board.legal_moves)

  # Black mobility
  board.turn = chess.BLACK
  mobility_black = sum(1 for _ in board.legal_moves)

  # Restore turn
  board.turn = saved_turn

  score = (mobility_white - mobility_black) * 0.05
  return score if perspective_color == chess.WHITE else -score


def mvv_lva_score(board: Board, move: Move) -> float:
  if not board.is_capture(move):
    return 0

  # victim square/type on the *current* board (pre-move)
  victim_type = board.piece_type_at(move.to_square)
  if victim_type is None and board.is_en_passant(move):
    victim_type = chess.PAWN  # en passant always captures a pawn

  if victim_type is None:
    return 0  # defensive

  attacker_type = board.piece_type_at(move.from_square)  # pre-move attacker
  victim_val = PIECE_VALUES[victim_type]
  attacker_val = PIECE_VALUES[attacker_type] if attacker_type else 1
  return (victim_val * 10) - attacker_val


def move_bonus(board: Board, perspective_color: bool) -> float:
  """Bonuses for the last move played (board already has the move pushed)."""
  if not board.move_stack:
    return 0.0

  move = board.peek()
  move_color = not board.turn  # side that just moved
  bonus = 0.0

  # Capture bonus
  if board.is_capture(move):
    # We need pre-move state to read attacker & victim
    board.pop()
    try:
      bonus = mvv_lva_score(board, move)
    finally:
      board.push(move)

  # Check bonus: after the move, if opponent is in check this returns True
  if board.is_check():
    bonus += MOVE_CHECK_BONUS

  # Promotion bonus
  if move.promotion:
    bonus += PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]

  # Flip perspective if the last move was by the opponent
  if move_color != perspective_color:
    bonus = -bonus

  return bonus
