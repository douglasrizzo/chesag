import chess


class ExtendedBoard(chess.Board):
  def extended_outcome(self) -> chess.Outcome | None:
    outcome = self.outcome(claim_draw=True)
    if outcome is not None:
      return outcome
    if self.has_insufficient_material(self.turn):
      return chess.Outcome(chess.Termination.INSUFFICIENT_MATERIAL, self.turn)
    return None

  def get_termination_reason(self) -> str:
    """Determine the reason for game termination."""
    board_outcome = self.extended_outcome()
    if board_outcome is not None:
      return board_outcome.termination.name
    return "Unknown"

  def extended_game_over(self) -> bool:
    return self.extended_outcome() is not None

  def evaluation(self) -> float:
    """Convert chess result string to numeric value from current player's perspective."""
    result = self.result()
    if result in {"*", "1/2-1/2"}:
      return 0.0
    if result == "1-0":
      return 1.0 if self.turn else -1.0
    if result == "0-1":
      return -1.0 if self.turn else 1.0
    return 0.0

  def material_balance(self) -> float:
    """Calculate material balance from white's perspective."""
    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

    balance = 0
    for square in chess.SQUARES:
      piece = self.piece_at(square)
      if piece:
        value = piece_values[piece.piece_type]
        balance += value if piece.color == chess.WHITE else -value

    return balance
