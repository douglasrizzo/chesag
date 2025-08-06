from collections import Counter
from dataclasses import dataclass

from chesag.game.results import GameResult


@dataclass
class GameStatistics:
  """Statistics for a series of games tracked by player rather than color."""

  total_games: int
  player1_wins: int
  player2_wins: int
  draws: int
  total_moves: int
  total_duration: float
  player1_agent: str
  player2_agent: str
  results: list[GameResult]

  @property
  def player1_win_rate(self) -> float:
    """Calculate Player 1's win rate as a percentage."""
    return (self.player1_wins / self.total_games) * 100 if self.total_games > 0 else 0.0

  @property
  def player2_win_rate(self) -> float:
    """Calculate Player 2's win rate as a percentage."""
    return (self.player2_wins / self.total_games) * 100 if self.total_games > 0 else 0.0

  @property
  def draw_rate(self) -> float:
    """Calculate draw rate as a percentage."""
    return (self.draws / self.total_games) * 100 if self.total_games > 0 else 0.0

  @property
  def avg_moves_per_game(self) -> float:
    """Calculate average moves per game."""
    return self.total_moves / self.total_games if self.total_games > 0 else 0.0

  @property
  def avg_duration_per_game(self) -> float:
    """Calculate average duration per game in seconds."""
    return self.total_duration / self.total_games if self.total_games > 0 else 0.0

  @property
  def player1_white_games(self) -> int:
    """Count how many games Player 1 played as white."""
    return sum(1 for result in self.results if result.player1_color == "white")

  @property
  def player1_black_games(self) -> int:
    """Count how many games Player 1 played as black."""
    return sum(1 for result in self.results if result.player1_color == "black")

  @property
  def player1_wins_as_white(self) -> int:
    """Count Player 1's wins when playing as white."""
    return sum(1 for result in self.results if result.player1_color == "white" and result.player1_result == "1-0")

  @property
  def player1_wins_as_black(self) -> int:
    """Count Player 1's wins when playing as black."""
    return sum(1 for result in self.results if result.player1_color == "black" and result.player1_result == "1-0")

  @property
  def player2_wins_as_white(self) -> int:
    """Count Player 2's wins when playing as white."""
    return sum(1 for result in self.results if result.player2_color == "white" and result.player2_result == "1-0")

  @property
  def player2_wins_as_black(self) -> int:
    """Count Player 2's wins when playing as black."""
    return sum(1 for result in self.results if result.player2_color == "black" and result.player2_result == "1-0")

  def report(self) -> None:
    """Print comprehensive game statistics."""
    # Termination reasons
    termination_counts = Counter(result.termination_reason for result in self.results)

    lines = [
      "",
      "=" * 60,
      "GAME STATISTICS",
      "=" * 60,
      f"Total Games: {self.total_games}",
      f"Player 1 Agent: {self.player1_agent}",
      f"Player 2 Agent: {self.player2_agent}",
      "",
      "RESULTS:",
      f"  Player 1 wins: {self.player1_wins:>3} ({self.player1_win_rate:>5.1f}%)",
      f"  Player 2 wins: {self.player2_wins:>3} ({self.player2_win_rate:>5.1f}%)",
      f"  Draws:         {self.draws:>3} ({self.draw_rate:>5.1f}%)",
      "",
      "PERFORMANCE:",
      f"  Average moves per game: {self.avg_moves_per_game:.1f}",
      f"  Average time per game:  {self.avg_duration_per_game:.1f}s",
      f"  Total time:             {self.total_duration:.1f}s",
      "",
      "TERMINATION REASONS:",
    ]

    for reason, count in sorted(termination_counts.items()):
      percentage = (count / self.total_games) * 100
      lines.append(f"  {reason:<20}: {count:>3} ({percentage:>5.1f}%)")

    if self.total_games > 1:
      lines.extend([
        "",
        "GAME-BY-GAME RESULTS:",
      ])
      for i, result in enumerate(self.results, 1):
        lines.append(f"Game {i}: {result}")

    report = "\n".join(lines)
    print(report)
