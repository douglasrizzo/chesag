import chess
from chess import Board

PIECE_VALUES = {
  chess.PAWN: 1.0,
  chess.KNIGHT: 3.0,
  chess.BISHOP: 3.0,
  chess.ROOK: 5.0,
  chess.QUEEN: 9.0,
  chess.KING: 0.0,
}


def symmetric_evaluation(board: Board) -> float:
  """Convert chess result string to numeric value from current player's perspective."""
  result = board.result()
  if result in {"*", "1/2-1/2"}:
    return 0.0
  if result == "1-0":
    return 1.0 if board.turn else -1.0
  if result == "0-1":
    return -1.0 if board.turn else 1.0
  return 0.0


def material_balance(board: Board) -> float:
  """Calculate material balance from the perspective of the player who last played."""
  balance = 0
  for square in chess.SQUARES:
    piece = board.piece_at(square)
    if piece:
      value = PIECE_VALUES[piece.piece_type]
      balance += value if piece.color != board.turn else -value

  return balance


def center_control(board: Board) -> float:
  """Calculate center control from the perspective of the player who last played."""
  # Center control (pawns and pieces attacking central squares)
  our_color = not board.turn
  center_squares = {chess.D4, chess.D5, chess.E4, chess.E5}
  center_control = 0

  for square in center_squares:
    # Check if we have a pawn on a central square
    piece = board.piece_at(square)
    if piece and piece.piece_type == chess.PAWN and our_color == piece.color:
      center_control += 0.3

    # Check attacks on central squares
    attackers = board.attackers(our_color, square)
    center_control += len(attackers) * 0.1

  return center_control


def king_safety(board: Board) -> float:
  """Calculate king safety from the perspective of the player who last played."""
  our_color = not board.turn
  king_safety = 0
  our_king_square = board.king(our_color)

  if our_king_square:
    # Penalize if our king is in check
    if board.is_check():
      king_safety -= 0.5

    # Reward castling rights
    if board.has_kingside_castling_rights(our_color):
      king_safety += 0.2
    if board.has_queenside_castling_rights(our_color):
      king_safety += 0.2

  return king_safety


def mobility_score(board: Board) -> float:
  """Calculate mobility score from the perspective of the player who last played."""
  return len(list(board.legal_moves)) * 0.05


def move_bonus(board: Board) -> float:
  """Calculate move bonus from the perspective of the player who last played."""
  our_color = not board.turn
  move = board.peek()
  move_bonus = 0

  # Bonus for captures
  if board.is_capture(move):
    # MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
    captured_piece = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if captured_piece:
      move_bonus += PIECE_VALUES[captured_piece.piece_type] * 0.1
    if attacker:
      # No bonus for attacking with the king
      attacker_bonus = 1 - PIECE_VALUES[attacker.piece_type] if attacker.piece_type != chess.KING else 0
      move_bonus += attacker_bonus * 0.1

    # Bonus if the capture makes the opponent have insufficient material
    board.pop()
    enemy_had_insufficient_material = board.has_insufficient_material(not our_color)
    board.push(move)
    if not enemy_had_insufficient_material and board.has_insufficient_material(not our_color):
      move_bonus += 0.5

  # Bonus for checks
  if board.is_check():
    move_bonus += 0.3

  # Bonus for promotions
  if move.promotion:
    move_bonus += PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]

  return move_bonus


def heuristic_evaluation(board: Board) -> float:
  """Evaluate a board based on chess heuristics from the perspective of the player who last played.

  Useful for evaluating possible moves by the current player.

  Parameters
  ----------
  board : Board
      The current board position

  Returns
  -------
  float
      A float representing the move's priority (higher values = better move)
  """
  # What color we are playing as
  our_color = not board.turn
  move = board.peek()

  # Check for immediate game-ending conditions
  if board.is_checkmate():
    # If we checkmated the opponent, this is the best possible outcome
    return float("inf")

  if board.is_stalemate() or board.is_insufficient_material():
    # Draw conditions - neutral evaluation
    return 0.0

  # 1. Material evaluation
  # 2. Center control
  # 3. King safety
  # 4. Mobility (number of legal moves available)
  # 5. Special move bonuses
  return (
    material_balance(board) + center_control(board) + king_safety(board) + mobility_score(board) + move_bonus(board)
  )
