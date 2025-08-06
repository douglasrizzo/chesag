from dataclasses import dataclass


@dataclass
class GameResult:
  """Represents the result of a single game with player-based tracking."""

  result: str  # "1-0", "0-1", "1/2-1/2", "*" (chess result from white's perspective)
  moves: int
  duration: float
  player1_agent: str
  player2_agent: str
  player1_color: str  # "white" or "black"
  player2_color: str  # "white" or "black"
  termination_reason: str

  @property
  def player1_result(self) -> str:
    """Get the game result from Player 1's perspective."""
    if self.result in {"1/2-1/2", "*"}:
      return self.result

    # Convert chess result to Player 1's perspective
    if self.player1_color == "white":
      return self.result  # Player 1 was white, so chess result is from their perspective
    # Player 1 was black, so flip the result
    if self.result == "1-0":
      return "0-1"  # White won, but Player 1 was black, so Player 1 lost
    if self.result == "0-1":
      return "1-0"  # Black won, and Player 1 was black, so Player 1 won

    return self.result

  @property
  def player2_result(self) -> str:
    """Get the game result from Player 2's perspective."""
    if self.result in {"1/2-1/2", "*"}:
      return self.result

    # Convert chess result to Player 2's perspective
    if self.player2_color == "white":
      return self.result  # Player 2 was white, so chess result is from their perspective
    # Player 2 was black, so flip the result
    if self.result == "1-0":
      return "0-1"  # White won, but Player 2 was black, so Player 2 lost
    if self.result == "0-1":
      return "1-0"  # Black won, and Player 2 was black, so Player 2 won

    return self.result

  def __str__(self) -> str:
    """Print the result of a single game."""
    # Determine who won from player perspective
    player1_result = self.player1_result
    if player1_result == "1-0":
      result_str = "Player 1 wins"
    elif player1_result == "0-1":
      result_str = "Player 2 wins"
    elif player1_result == "1/2-1/2":
      result_str = "Draw"
    else:
      result_str = "Unfinished"

    return (
      f"{result_str} ({self.result}) - "
      f"P1 as {self.player1_color}, {self.moves} moves, {self.duration:.1f}s - {self.termination_reason}"
    )
