from abc import ABC, abstractmethod

import chess
from chess import Board, Move

PIECE_VALUES = {
  chess.PAWN: 1.0,
  chess.KNIGHT: 3.0,
  chess.BISHOP: 3.0,
  chess.ROOK: 5.0,
  chess.QUEEN: 9.0,
  chess.KING: 0.0,
}


class MovePrioritizer(ABC):
  def evaluate_move(self, move: Move, board: Board) -> float:
    board.push(move)
    priority = self.evaluate_board(board)
    board.pop()
    return priority

  @abstractmethod
  def evaluate_board(self, board: Board) -> float:
    msg = "Subclasses must implement evaluate_board"
    raise NotImplementedError(msg)

  def order_moves(self, board: Board, moves: list[Move]) -> list[Move]:
    return sorted(moves, key=lambda move: self.evaluate_move(move, board), reverse=True)


class HeuristicMovePrioritizer(MovePrioritizer):
  """A move prioritizer that uses chess heuristics to evaluate and order moves."""

  def evaluate_board(self, board: Board) -> float:
    """Evaluate a board based on chess heuristics and return a priority score.

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
    material = material_score(board)

    # 2. Positional factors
    # Center control (pawns and pieces attacking central squares)
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

    # 3. King safety
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

    # 4. Mobility (number of legal moves available)
    mobility_score = len(list(board.legal_moves)) * 0.05

    # 5. Special move bonuses
    move_bonus = 0

    # Bonus for captures
    if board.is_capture(move):
      captured_piece = board.piece_at(move.to_square)
      if captured_piece:
        move_bonus += PIECE_VALUES[captured_piece.piece_type] * 0.1
      # Bonus if the capture makes the opponent's have insufficient material
      if not board.has_insufficient_material(not our_color) and board.has_insufficient_material(not our_color):
        move_bonus += 0.5

    # Bonus for checks
    if board.is_check():
      move_bonus += 0.3

    # Bonus for promotions
    if move.promotion:
      move_bonus += PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]

    return material + center_control + king_safety + mobility_score + move_bonus

  def __str__(self) -> str:
    return self.__class__.__name__


def material_score(board: chess.Board):
  # Count material for both sides
  white_material = 0
  black_material = 0

  for square in chess.SQUARES:
    piece = board.piece_at(square)
    if piece:
      value = PIECE_VALUES[piece.piece_type]
      if piece.color == chess.WHITE:
        white_material += value
      else:
        black_material += value

  # Material advantage from current player's perspective
  if board.turn == chess.BLACK:  # Previous move was by white
    return white_material - black_material
  # Previous move was by black
  return black_material - white_material
