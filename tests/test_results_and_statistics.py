import pytest

from chesag.game.results import GameResult
from chesag.game.statistics import GameStatistics


def test_game_result_flips_player_perspective() -> None:
  result = GameResult(
    result="0-1",
    moves=42,
    duration=3.5,
    player1_agent="A",
    player2_agent="B",
    player1_color="black",
    player2_color="white",
    termination_reason="CHECKMATE",
  )

  assert result.player1_result == "1-0"
  assert result.player2_result == "0-1"
  assert "Player 1/Black/A wins" in str(result)


def test_game_statistics_computes_rates_and_color_splits() -> None:
  results = [
    GameResult("1-0", 20, 1.0, "A", "B", "white", "black", "CHECKMATE"),
    GameResult("0-1", 30, 2.0, "A", "B", "black", "white", "CHECKMATE"),
    GameResult("1/2-1/2", 40, 3.0, "A", "B", "white", "black", "STALEMATE"),
  ]
  stats = GameStatistics(
    total_games=3,
    player1_wins=2,
    player2_wins=0,
    draws=1,
    total_moves=90,
    total_duration=6.0,
    player1_agent="A",
    player2_agent="B",
    results=results,
  )

  assert stats.player1_win_rate == pytest.approx(66.66666666666666)
  assert stats.draw_rate == pytest.approx(33.33333333333333)
  assert stats.avg_moves_per_game == pytest.approx(30.0)
  assert stats.player1_white_games == 2
  assert stats.player1_black_games == 1
  assert stats.player1_wins_as_white == 1
  assert stats.player1_wins_as_black == 1


def test_game_statistics_report_returns_string() -> None:
  stats = GameStatistics(
    total_games=1,
    player1_wins=1,
    player2_wins=0,
    draws=0,
    total_moves=12,
    total_duration=1.2,
    player1_agent="A",
    player2_agent="B",
    results=[GameResult("1-0", 12, 1.2, "A", "B", "white", "black", "CHECKMATE")],
  )

  report = stats.report()

  assert isinstance(report, str)
  assert "GAME STATISTICS" in report
