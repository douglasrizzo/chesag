import chess
from chess import Board

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
CENTER_SQUARES = {chess.D4, chess.D5, chess.E4, chess.E5}
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


def evaluate(board: Board, perspective_color: bool, include_move_bonus: bool = False) -> float:
  """
  Evaluate board from perspective_color's point of view.
  Positive = good for perspective_color, Negative = good for opponent.

  Parameters
  ----------
  board : chess.Board
  perspective_color : bool
      chess.WHITE or chess.BLACK
  include_move_bonus : bool
      If True, adds bonuses based on the last move played.
  """
  # --- Terminal conditions ---
  if board.is_checkmate():
    return float("inf") if board.turn != perspective_color else -float("inf")
  if board.is_stalemate() or board.is_insufficient_material():
    return 0.0

  # --- Material score ---
  score = material_balance(board, perspective_color)

  # --- Bishop pair bonus ---
  if len(board.pieces(chess.BISHOP, perspective_color)) >= 2:
    score += BISHOP_PAIR_BONUS
  if len(board.pieces(chess.BISHOP, not perspective_color)) >= 2:
    score -= BISHOP_PAIR_BONUS

  # --- Passed pawns ---
  score += passed_pawn_score(board, perspective_color)

  # --- Center control ---
  score += center_control(board, perspective_color)

  # --- King safety ---
  score += king_safety(board, perspective_color)

  # --- Mobility ---
  score += mobility_score(board, perspective_color)

  # --- Move-specific bonuses ---
  if include_move_bonus and board.move_stack:
    score += move_bonus(board, perspective_color)

  return score


def material_balance(board: Board, color: bool) -> float:
  score = 0
  for piece_type, value in PIECE_VALUES.items():
    score += value * len(board.pieces(piece_type, color))
    score -= value * len(board.pieces(piece_type, not color))
  return score


def passed_pawn_score(board: Board, color: bool) -> float:
  bonus = 0.0
  for pawn_square in board.pieces(chess.PAWN, color):
    if is_passed_pawn(board, pawn_square, color):
      rank = chess.square_rank(pawn_square) if color == chess.WHITE else 7 - chess.square_rank(pawn_square)
      bonus += PASSED_PAWN_BONUS * (rank / 6)
  for pawn_square in board.pieces(chess.PAWN, not color):
    if is_passed_pawn(board, pawn_square, not color):
      rank = chess.square_rank(pawn_square) if color != chess.WHITE else 7 - chess.square_rank(pawn_square)
      bonus -= PASSED_PAWN_BONUS * (rank / 6)
  return bonus


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


def center_control(board: Board, color: bool) -> float:
  score = 0.0
  for square in EXTENDED_CENTER:
    attackers_ours = len(board.attackers(color, square))
    attackers_theirs = len(board.attackers(not color, square))
    score += (attackers_ours - attackers_theirs) * CENTER_CONTROL_WEIGHT
  return score


def king_safety(board: Board, color: bool) -> float:
  score = 0.0
  king_square = board.king(color)
  if king_square is None:
    return score

  # Castling rights
  if board.has_kingside_castling_rights(color):
    score += KING_CASTLE_BONUS
  if board.has_queenside_castling_rights(color):
    score += KING_CASTLE_BONUS

  # Open files near king
  king_file = chess.square_file(king_square)
  for f in (king_file - 1, king_file, king_file + 1):
    if 0 <= f <= 7:
      file_squares = [chess.square(f, r) for r in range(8)]
      if not any(board.piece_type_at(sq) == chess.PAWN and board.color_at(sq) == color for sq in file_squares):
        score += KING_OPEN_FILE_PENALTY

  # Pawn shield in front of king
  forward = 1 if color == chess.WHITE else -1
  shield_ranks = [
    chess.square(king_file + df, chess.square_rank(king_square) + forward)
    for df in (-1, 0, 1)
    if 0 <= king_file + df <= 7
  ]
  for sq in shield_ranks:
    if board.piece_type_at(sq) != chess.PAWN or board.color_at(sq) != color:
      score += PAWN_SHIELD_PENALTY

  return score


def mobility_score(board: Board, color: bool) -> float:
  # Generate moves without changing turn
  board_turn = board.turn
  board.turn = color
  mobility_ours = sum(1 for _ in board.legal_moves)
  board.turn = not color
  mobility_theirs = sum(1 for _ in board.legal_moves)
  board.turn = board_turn
  return (mobility_ours - mobility_theirs) * 0.05


def move_bonus(board: Board, perspective_color: bool) -> float:
  """Bonuses for the last move played, from perspective_color's POV."""
  move = board.peek()
  move_color = not board.turn  # player who made the move
  bonus = 0.0

  # Bonus for captures
  if board.is_capture(move):
    captured_piece_type = board.piece_type_at(move.to_square)
    attacker_piece_type = board.piece_type_at(move.from_square)  # after move, so None
    # Need to detect attacker from before move
    board.pop()
    attacker_piece_type = board.piece_type_at(move.from_square)
    board.push(move)

    if captured_piece_type:
      bonus_value = PIECE_VALUES[captured_piece_type] * MOVE_CAPTURE_WEIGHT
      bonus += bonus_value if move_color == perspective_color else -bonus_value
    if attacker_piece_type and attacker_piece_type != chess.KING:
      attacker_bonus = (1 - PIECE_VALUES[attacker_piece_type]) * MOVE_CAPTURE_WEIGHT
      bonus += attacker_bonus if move_color == perspective_color else -attacker_bonus

  # Bonus for checks
  if board.is_check():
    bonus += MOVE_CHECK_BONUS if move_color == perspective_color else -MOVE_CHECK_BONUS

  # Bonus for promotions
  if move.promotion:
    promo_bonus = PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]
    bonus += promo_bonus if move_color == perspective_color else -promo_bonus

  return bonus
