from __future__ import annotations

from collections import Counter

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from chesag.game.results import GameResult
from chesag.game.statistics import GameStatistics

PLAYER_COLORS = ("white", "black")
DECISIVE_RESULTS = ("1-0", "0-1")
FINISHED_RESULTS = ("1-0", "0-1", "1/2-1/2")
ALL_RESULTS = ("1-0", "0-1", "1/2-1/2", "*")
TERMINATION_REASONS = ("CHECKMATE", "STALEMATE", "RESIGNATION", "TIMEOUT")


@st.composite
def game_results(
  draw: st.DrawFn,
  *,
  include_unfinished: bool = True,
) -> GameResult:
  player1_color = draw(st.sampled_from(PLAYER_COLORS))
  player2_color = "black" if player1_color == "white" else "white"
  result_pool = ALL_RESULTS if include_unfinished else FINISHED_RESULTS
  result = draw(st.sampled_from(result_pool))

  return GameResult(
    result=result,
    moves=draw(st.integers(min_value=0, max_value=400)),
    duration=draw(
      st.floats(
        min_value=0.0,
        max_value=7_200.0,
        allow_nan=False,
        allow_infinity=False,
      ),
    ),
    player1_agent="agent-a",
    player2_agent="agent-b",
    player1_color=player1_color,
    player2_color=player2_color,
    termination_reason=draw(st.sampled_from(TERMINATION_REASONS)),
  )


@st.composite
def game_statistics(draw: st.DrawFn) -> GameStatistics:
  results = draw(st.lists(game_results(include_unfinished=False), max_size=12))
  player1_wins = sum(result.player1_result == "1-0" for result in results)
  player2_wins = sum(result.player2_result == "1-0" for result in results)
  draws = sum(result.result == "1/2-1/2" for result in results)
  total_games = len(results)

  return GameStatistics(
    total_games=total_games,
    player1_wins=player1_wins,
    player2_wins=player2_wins,
    draws=draws,
    total_moves=sum(result.moves for result in results),
    total_duration=sum(result.duration for result in results),
    player1_agent="agent-a",
    player2_agent="agent-b",
    results=results,
  )


def _swap_players(result: GameResult) -> GameResult:
  return GameResult(
    result=result.result,
    moves=result.moves,
    duration=result.duration,
    player1_agent=result.player2_agent,
    player2_agent=result.player1_agent,
    player1_color=result.player2_color,
    player2_color=result.player1_color,
    termination_reason=result.termination_reason,
  )


@given(game_results())
@example(
  GameResult(
    result="0-1",
    moves=42,
    duration=3.5,
    player1_agent="agent-a",
    player2_agent="agent-b",
    player1_color="black",
    player2_color="white",
    termination_reason="CHECKMATE",
  ),
)
@example(
  GameResult(
    result="*",
    moves=0,
    duration=0.0,
    player1_agent="agent-a",
    player2_agent="agent-b",
    player1_color="white",
    player2_color="black",
    termination_reason="TIMEOUT",
  ),
)
def test_game_result_player_views_are_consistent(result: GameResult) -> None:
  if result.result in DECISIVE_RESULTS:
    assert {result.player1_result, result.player2_result} == set(DECISIVE_RESULTS)
    assert result.player1_result != result.player2_result
  else:
    assert result.player1_result == result.result
    assert result.player2_result == result.result

  swapped = _swap_players(result)
  assert result.player1_result == swapped.player2_result
  assert result.player2_result == swapped.player1_result


@given(game_results())
@example(
  GameResult(
    result="1/2-1/2",
    moves=80,
    duration=12.5,
    player1_agent="agent-a",
    player2_agent="agent-b",
    player1_color="white",
    player2_color="black",
    termination_reason="STALEMATE",
  ),
)
def test_game_result_string_matches_outcome(result: GameResult) -> None:
  rendered = str(result)

  assert f"{result.moves} moves" in rendered
  assert f"{result.duration:.1f}s" in rendered
  assert result.termination_reason in rendered

  if result.player1_result == "1-0":
    assert f"Player 1/{result.player1_color.capitalize()}/{result.player1_agent} wins" in rendered
  elif result.player1_result == "0-1":
    assert f"Player 2/{result.player2_color.capitalize()}/{result.player2_agent} wins" in rendered
  elif result.result == "1/2-1/2":
    assert "Draw" in rendered
  else:
    assert "Unfinished" in rendered


@given(game_statistics())
@example(
  GameStatistics(
    total_games=0,
    player1_wins=0,
    player2_wins=0,
    draws=0,
    total_moves=0,
    total_duration=0.0,
    player1_agent="agent-a",
    player2_agent="agent-b",
    results=[],
  ),
)
def test_game_statistics_aggregates_match_results(stats: GameStatistics) -> None:
  assert stats.player1_white_games + stats.player1_black_games == stats.total_games
  assert stats.player1_wins_as_white + stats.player1_wins_as_black == stats.player1_wins
  assert stats.player2_wins_as_white + stats.player2_wins_as_black == stats.player2_wins

  if stats.total_games == 0:
    assert stats.player1_win_rate == 0.0
    assert stats.player2_win_rate == 0.0
    assert stats.draw_rate == 0.0
    assert stats.avg_moves_per_game == 0.0
    assert stats.avg_duration_per_game == 0.0
    return

  assert stats.player1_wins + stats.player2_wins + stats.draws == stats.total_games
  assert stats.player1_win_rate + stats.player2_win_rate + stats.draw_rate == pytest.approx(100.0)
  assert stats.avg_moves_per_game == stats.total_moves / stats.total_games
  assert stats.avg_duration_per_game == stats.total_duration / stats.total_games


@given(game_statistics())
@example(
  GameStatistics(
    total_games=2,
    player1_wins=1,
    player2_wins=0,
    draws=1,
    total_moves=52,
    total_duration=3.0,
    player1_agent="agent-a",
    player2_agent="agent-b",
    results=[
      GameResult("1-0", 20, 1.0, "agent-a", "agent-b", "white", "black", "CHECKMATE"),
      GameResult("1/2-1/2", 32, 2.0, "agent-a", "agent-b", "black", "white", "STALEMATE"),
    ],
  ),
)
def test_game_statistics_report_contains_consistent_summary(stats: GameStatistics) -> None:
  report = stats.report()

  assert "GAME STATISTICS" in report
  assert f"Total Games: {stats.total_games}" in report
  assert f"Player 1 Agent: {stats.player1_agent}" in report
  assert f"Player 2 Agent: {stats.player2_agent}" in report

  termination_counts = Counter(result.termination_reason for result in stats.results)
  for reason, count in termination_counts.items():
    assert reason in report
    assert f": {count:>3} (" in report

  if stats.total_games > 1:
    for index, result in enumerate(stats.results, start=1):
      assert f"Game {index}: {result}" in report
  else:
    assert "GAME-BY-GAME RESULTS:" not in report
