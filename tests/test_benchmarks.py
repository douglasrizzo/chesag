from typing import cast

import chess

from chesag.benchmarks import benchmark_evaluation_tiers, benchmark_mcts, benchmark_minimax, run_smoke_match
from chesag.evaluation import get_evaluation_stats, reset_evaluation_stats


def test_evaluation_stats_count_tier_calls() -> None:
  reset_evaluation_stats()

  result = benchmark_evaluation_tiers(chess.STARTING_FEN, iterations=3)
  stats = get_evaluation_stats()

  assert result.repetitions == 3
  assert stats.leaf.calls == 3
  assert stats.order.calls == 3
  assert stats.rollout.calls == 3


def test_minimax_benchmark_exposes_search_stats() -> None:
  result = benchmark_minimax(chess.STARTING_FEN, depth=1, repetitions=1)

  runs = cast("list[dict[str, object]]", result.details["runs"])
  run = runs[0]
  assert result.name == "minimax"
  assert "move" in run
  assert "search" in run


def test_mcts_benchmark_exposes_cache_details() -> None:
  result = benchmark_mcts(chess.STARTING_FEN, num_simulations=1, repetitions=1, use_transposition_table=False)

  runs = cast("list[dict[str, object]]", result.details["runs"])
  run = runs[0]
  assert result.name == "mcts"
  assert run["cache_size"] == 0


def test_smoke_match_returns_report() -> None:
  result = run_smoke_match("random", "random", games=1)
  report = cast("str", result["report"])

  assert result["games"] == 1
  assert "GAME STATISTICS" in report
