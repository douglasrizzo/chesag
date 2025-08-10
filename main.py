from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from tqdm import tqdm

from chesag.agents import AGENTS
from chesag.game import Game
from chesag.game.statistics import GameStatistics
from chesag.logging import get_logger
from chesag.replay import replay
from chesag.viewer import ChessViewer

logger = get_logger()


def play(
  player1: str,
  player2: str | None,
  fen: str | None = None,
  num_games: int = 1,
  verbose: bool = True,
  visual: bool = False,
  move_delay: float = 1.0,
) -> None:
  """Play one or more games between two agents with color swapping for fairness."""
  # Initialize agents
  player1_agent = AGENTS[player1]()
  player2_agent = AGENTS[player2]() if player2 else player1_agent

  # Initialize viewer if visual mode is enabled
  viewer = None
  if visual:
    viewer = ChessViewer()
    viewer.initialize()

  # Track statistics
  results = []
  player1_wins = 0
  player2_wins = 0
  draws = 0
  total_moves = 0
  total_duration = 0.0

  logger.info(
    "Playing %d game%s between %s (Player 1) and %s (Player 2)",
    num_games,
    "s" if num_games != 1 else "",
    player1,
    player2 or player1,
  )
  logger.info("Players will alternate colors for fairness.")
  if fen:
    logger.info("Starting position: %s", fen)

  # Main game loop with overall progress bar
  with tqdm(total=num_games, desc="Overall Progress", unit="games") as overall_pbar:
    for game_num in range(1, num_games + 1):
      # Alternate colors: Player 1 is white on odd games, black on even games
      player1_is_white = (game_num % 2) == 1

      game = Game(
        player1_agent=player1_agent,
        player2_agent=player2_agent,
        fen=fen,
        player1_is_white=player1_is_white,
        viewer=viewer,
        move_delay=move_delay,
      )

      # Play the game
      game_result = game.play(game_num)
      results.append(game_result)

      # Update statistics
      total_moves += game_result.moves
      total_duration += game_result.duration

      # Count wins from player perspective, not color
      player1_result = game_result.player1_result
      if player1_result == "1-0":
        player1_wins += 1
      elif player1_result == "0-1":
        player2_wins += 1
      elif player1_result == "1/2-1/2":
        draws += 1

      msg = f"Game: {game_result}"
      logger.info(msg)
      overall_pbar.update(1)

  # Clean up agents
  player1_agent.close()
  player2_agent.close()

  # Clean up viewer
  if viewer is not None:
    viewer.close()

  # Create and print statistics
  stats = GameStatistics(
    total_games=num_games,
    player1_wins=player1_wins,
    player2_wins=player2_wins,
    draws=draws,
    total_moves=total_moves,
    total_duration=total_duration,
    player1_agent=str(player1_agent),
    player2_agent=str(player2_agent),
    results=results,
  )

  # Always print statistics for multiple games, or if requested for single game
  if num_games > 1 or verbose:
    report = stats.report()
    logger.info(report)


def train(args: object) -> None:
  """Train the model (not implemented yet)."""
  msg = "Training is not implemented yet"
  raise NotImplementedError(msg)


if __name__ == "__main__":
  # Create an argument parser with two subparsers for train and play
  parser = ArgumentParser(description="RL Chess", formatter_class=ArgumentDefaultsHelpFormatter)
  subparsers = parser.add_subparsers(dest="command", help="Available commands")

  # Train subparser
  train_parser = subparsers.add_parser("train", help="Train the model")
  train_parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
  train_parser.add_argument("--batch_size", type=int, default=32, help="Batch size")

  # Play subparser
  play_parser = subparsers.add_parser("play", help="Play game(s) between two agents")
  agent_choices = list(AGENTS.keys())
  play_parser.add_argument("player1", type=str, choices=agent_choices, help="Player 1 agent")
  play_parser.add_argument("--player2", type=str, choices=agent_choices, default=None, help="Player 2 agent")
  play_parser.add_argument("--fen", type=str, default=None, help="Starting FEN position")
  play_parser.add_argument("--games", type=int, default=1, help="Number of games to play")
  play_parser.add_argument("--quiet", action="store_true", help="Only show final statistics")
  play_parser.add_argument("--visual", action="store_true", help="Show visual chess board during games")
  play_parser.add_argument("--move-delay", type=float, default=0.0, help="Delay between moves in visual mode (seconds)")

  # Replay subparser
  replay_parser = subparsers.add_parser("replay", help="Replay game(s) from a PGN file")
  replay_parser.add_argument("pgn_file", type=str, help="PGN file to replay")
  replay_parser.add_argument(
    "--move-delay", type=float, default=0.0, help="Delay between moves in visual mode (seconds)"
  )

  # Parse arguments
  args = parser.parse_args()

  # Execute command
  if args.command == "train":
    train(args)
  elif args.command == "play":
    play(
      args.player1,
      args.player2,
      args.fen,
      args.games,
      verbose=not args.quiet,
      visual=args.visual,
      move_delay=args.move_delay,
    )
  elif args.command == "replay":
    replay(pgn_file=args.pgn_file, move_delay=args.move_delay)
  else:
    parser.print_help()
