"""Local benchmark and smoke helpers for search validation."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass

import chess

from chesag.agents import AGENTS
from chesag.agents.mcts.agent import MCTSAgent
from chesag.agents.minimax import MinimaxAgent
from chesag.evaluation import (
  get_evaluation_stats,
  leaf_evaluate,
  order_evaluate,
  reset_evaluation_stats,
  rollout_evaluate,
)
from chesag.game import Game
from chesag.game.statistics import GameStatistics


@dataclass(slots=True)
class BenchmarkResult:
  """Serializable benchmark result."""

  name: str
  repetitions: int
  elapsed_seconds: float
  details: dict[str, object]


def benchmark_evaluation_tiers(fen: str, iterations: int = 200) -> BenchmarkResult:
  """Benchmark all evaluation tiers on a fixed position."""
  board = chess.Board(fen)
  reset_evaluation_stats()
  start = time.perf_counter()

  for _ in range(iterations):
    leaf_evaluate(board, board.turn)
    order_evaluate(board, board.turn)
    rollout_evaluate(board, board.turn)

  elapsed = time.perf_counter() - start
  return BenchmarkResult(
    name="evaluation_tiers",
    repetitions=iterations,
    elapsed_seconds=elapsed,
    details={"fen": fen, "stats": asdict(get_evaluation_stats())},
  )


def benchmark_minimax(fen: str, *, depth: int = 3, repetitions: int = 2) -> BenchmarkResult:
  """Benchmark minimax search and expose node/TT stats."""
  agent = MinimaxAgent(maxdepth=depth)
  board = chess.Board(fen)
  runs: list[dict[str, object]] = []
  start = time.perf_counter()

  for _ in range(repetitions):
    run_board = board.copy()
    move = agent.get_move(run_board)
    runs.append({
      "move": move.uci(),
      "search": agent.last_search.as_dict(),
      "tt_size": len(agent._tt),
    })

  elapsed = time.perf_counter() - start
  return BenchmarkResult(
    name="minimax",
    repetitions=repetitions,
    elapsed_seconds=elapsed,
    details={"fen": fen, "depth": depth, "runs": runs},
  )


def benchmark_mcts(
  fen: str,
  *,
  num_simulations: int = 100,
  repetitions: int = 2,
  use_transposition_table: bool = True,
) -> BenchmarkResult:
  """Benchmark MCTS search and expose cache reuse details."""
  agent = MCTSAgent(
    num_simulations=num_simulations,
    use_transposition_table=use_transposition_table,
  )
  board = chess.Board(fen)
  runs: list[dict[str, object]] = []
  start = time.perf_counter()

  for _ in range(repetitions):
    run_board = board.copy()
    move = agent.get_move(run_board)
    cache_size = 0
    if agent.mcts_searcher.transposition_table is not None:
      cache_size = len(agent.mcts_searcher.transposition_table)
    runs.append({"move": move.uci(), "cache_size": cache_size})

  elapsed = time.perf_counter() - start
  agent.close()
  return BenchmarkResult(
    name="mcts",
    repetitions=repetitions,
    elapsed_seconds=elapsed,
    details={
      "fen": fen,
      "num_simulations": num_simulations,
      "use_transposition_table": use_transposition_table,
      "runs": runs,
    },
  )


def run_smoke_match(
  player1: str,
  player2: str,
  *,
  games: int = 2,
  fen: str | None = None,
) -> dict[str, object]:
  """Run a small smoke match and return summary statistics."""
  player1_agent = AGENTS[player1]()
  player2_agent = AGENTS[player2]()
  results = []
  player1_wins = 0
  player2_wins = 0
  draws = 0
  total_moves = 0
  total_duration = 0.0

  try:
    for game_num in range(1, games + 1):
      game = Game(
        player1_agent=player1_agent,
        player2_agent=player2_agent,
        fen=fen,
        player1_is_white=(game_num % 2) == 1,
      )
      result = game.play(game_num=game_num)
      results.append(result)
      total_moves += result.moves
      total_duration += result.duration
      if result.player1_result == "1-0":
        player1_wins += 1
      elif result.player1_result == "0-1":
        player2_wins += 1
      else:
        draws += 1
  finally:
    player1_agent.close()
    player2_agent.close()

  stats = GameStatistics(
    total_games=games,
    player1_wins=player1_wins,
    player2_wins=player2_wins,
    draws=draws,
    total_moves=total_moves,
    total_duration=total_duration,
    player1_agent=player1,
    player2_agent=player2,
    results=results,
  )
  return {
    "player1": player1,
    "player2": player2,
    "games": games,
    "fen": fen,
    "report": stats.report(),
  }


def main() -> None:
  """Run local benchmark helpers from the command line."""
  parser = argparse.ArgumentParser(description="chesag benchmark helpers")
  subparsers = parser.add_subparsers(dest="command", required=True)

  eval_parser = subparsers.add_parser("eval", help="Benchmark evaluation tiers")
  eval_parser.add_argument("--fen", default=chess.STARTING_FEN)
  eval_parser.add_argument("--iterations", type=int, default=200)

  minimax_parser = subparsers.add_parser("minimax", help="Benchmark minimax search")
  minimax_parser.add_argument("--fen", default=chess.STARTING_FEN)
  minimax_parser.add_argument("--depth", type=int, default=3)
  minimax_parser.add_argument("--repetitions", type=int, default=2)

  mcts_parser = subparsers.add_parser("mcts", help="Benchmark MCTS search")
  mcts_parser.add_argument("--fen", default=chess.STARTING_FEN)
  mcts_parser.add_argument("--simulations", type=int, default=100)
  mcts_parser.add_argument("--repetitions", type=int, default=2)
  mcts_parser.add_argument("--no-tt", action="store_true")

  smoke_parser = subparsers.add_parser("smoke", help="Run a small agent-vs-agent smoke match")
  smoke_parser.add_argument("player1", choices=sorted(AGENTS))
  smoke_parser.add_argument("player2", choices=sorted(AGENTS))
  smoke_parser.add_argument("--games", type=int, default=2)
  smoke_parser.add_argument("--fen", default=None)

  args = parser.parse_args()
  if args.command == "eval":
    result = benchmark_evaluation_tiers(args.fen, iterations=args.iterations)
    print(json.dumps(asdict(result), indent=2))
  elif args.command == "minimax":
    result = benchmark_minimax(args.fen, depth=args.depth, repetitions=args.repetitions)
    print(json.dumps(asdict(result), indent=2))
  elif args.command == "mcts":
    result = benchmark_mcts(
      args.fen,
      num_simulations=args.simulations,
      repetitions=args.repetitions,
      use_transposition_table=not args.no_tt,
    )
    print(json.dumps(asdict(result), indent=2))
  else:
    print(json.dumps(run_smoke_match(args.player1, args.player2, games=args.games, fen=args.fen), indent=2))


if __name__ == "__main__":
  main()
