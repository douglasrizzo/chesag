"""MCTS agent and configuration."""

from __future__ import annotations

import warnings

from chess import Board, Move

from chesag.agents import BaseAgent
from chesag.agents.mcts.algorithm import MCTSSearcher
from chesag.evaluation import material_balance
from chesag.logging import get_logger

logger = get_logger()


class MCTSConfig:
  """Configuration for the live MCTS behavior."""

  def __init__(
    self,
    num_simulations: int = 100,
    c_puct: float = 1.4,
    use_transposition_table: bool = True,
    resign_threshold: float | None = None,
    *,
    parallel: bool | None = None,
    num_workers: int | None = None,
    rollouts_per_leaf: int | None = None,
    use_pruning: bool | None = None,
  ) -> None:
    """Initialize the MCTS configuration.

    Deprecated knobs are accepted for compatibility, but only live options are stored.
    """
    if parallel is not None or num_workers is not None or rollouts_per_leaf is not None:
      warnings.warn(
        "parallel, num_workers, and rollouts_per_leaf are no longer supported and are ignored",
        DeprecationWarning,
        stacklevel=2,
      )
    if use_pruning is not None:
      warnings.warn(
        "use_pruning is deprecated; use use_transposition_table instead",
        DeprecationWarning,
        stacklevel=2,
      )
      use_transposition_table = use_pruning

    self.num_simulations = num_simulations
    self.c_puct = c_puct
    self.use_transposition_table = use_transposition_table
    self.resign_threshold = min(resign_threshold, -resign_threshold) if resign_threshold is not None else float("-inf")

  def __str__(self) -> str:
    """Return a concise string representation of the config."""
    return f"sims={self.num_simulations}, c_puct={self.c_puct}, tt={self.use_transposition_table}"


class MCTSAgent(BaseAgent):
  """Monte Carlo Tree Search agent for chess."""

  def __init__(
    self,
    config: MCTSConfig | None = None,
    *,
    num_simulations: int = 100,
    c_puct: float = 1.4,
    use_transposition_table: bool = True,
    resign_threshold: float | None = None,
    parallel: bool | None = None,
    num_workers: int | None = None,
    rollouts_per_leaf: int | None = None,
    use_pruning: bool | None = None,
  ) -> None:
    """Initialize the MCTS agent."""
    if config is None:
      config = MCTSConfig(
        num_simulations=num_simulations,
        c_puct=c_puct,
        use_transposition_table=use_transposition_table,
        resign_threshold=resign_threshold,
        parallel=parallel,
        num_workers=num_workers,
        rollouts_per_leaf=rollouts_per_leaf,
        use_pruning=use_pruning,
      )
    self.config = config
    self.mcts_searcher = MCTSSearcher(use_transposition_table=self.config.use_transposition_table)

  def get_move(self, board: Board) -> Move:
    """Get the best move for the current board position using MCTS."""
    if material_balance(board, board.turn) < self.config.resign_threshold:
      return Move.null()
    move_and_eval = self.mcts_searcher.should_return_single_move(board)
    if move_and_eval is not None:
      return move_and_eval[0]

    root = self.mcts_searcher.create_root_node(board)
    self.mcts_searcher.search(root, self.config.num_simulations, self.config.c_puct)
    return self.mcts_searcher.get_best_child(root)[0]

  def close(self) -> None:
    """Persist any MCTS cache state before shutdown."""
    self.mcts_searcher.save_cache()
    logger.info("Closing MCTSAgent, transposition table saved")

  def __str__(self) -> str:
    """Return a string representation of the agent."""
    return f"MCTSAgent({self.config})"

  def __repr__(self) -> str:
    """Return a detailed string representation of the agent."""
    return f"MCTSAgent(config={self.config!r})"
