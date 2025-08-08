from chess import Board, Move

from chesag.agents import BaseAgent
from chesag.agents.mcts.algorithm import MCTSSearcher
from chesag.agents.mcts.move_selection import MoveSelectionStrategy
from chesag.evaluation import material_balance
from chesag.logging import get_logger

logger = get_logger()


class MCTSConfig:
  """Configuration class for MCTS parameters."""

  def __init__(
    self,
    num_simulations: int = 100,
    c_puct: float = 1.4,
    parallel: bool = True,
    num_workers: int | None = None,
    rollouts_per_leaf: int = 4,
    use_pruning: bool = True,
    resign_threshold: float = 6.0,
  ):
    self.num_simulations = num_simulations
    self.c_puct = c_puct
    self.parallel = parallel
    self.num_workers = num_workers
    self.rollouts_per_leaf = rollouts_per_leaf
    self.use_pruning = use_pruning
    self.resign_threshold = resign_threshold

  def __str__(self) -> str:
    """Return a string representation of the config."""
    pruning_str = f", pruning={self.use_pruning}"
    if self.parallel:
      return f"sims={self.num_simulations}, c_puct={self.c_puct}{pruning_str}"
    return (
      f"sims={self.num_simulations}, c_puct={self.c_puct}, "
      f"parallel={self.parallel}, workers={self.num_workers}{pruning_str}"
    )


class MCTSAgent(BaseAgent):
  """Monte Carlo Tree Search agent for chess.

  This agent uses Monte Carlo Tree Search (MCTS) algorithm to select moves
  by building a search tree and using simulations to evaluate positions.
  """

  def __init__(self, config: MCTSConfig | None = None, **kwargs) -> None:
    """Initialize the MCTS agent.

    Parameters
    ----------
    config : MCTSConfig | None, optional
        MCTS configuration object, by default None (uses default config)
    **kwargs
        Configuration parameters if config is not provided
    """
    if config is None:
      config = MCTSConfig(**kwargs)
    self.config = config
    self.mcts_searcher = MCTSSearcher(MoveSelectionStrategy.ACTION)

  def get_move(self, board: Board) -> Move:
    """Get the best move for the current board position using MCTS."""
    if material_balance(board) > self.config.resign_threshold:
      return Move.null()
    move_and_eval = self.mcts_searcher.should_return_single_move(board)
    if move_and_eval:
      return move_and_eval[0]

    root = self.mcts_searcher.create_root_node(board)
    self.mcts_searcher.search(root, self.config.num_simulations, self.config.c_puct)
    return self.mcts_searcher.get_best_child(root)[0]

  def close(self):
    self.mcts_searcher.save_cache()
    logger.info("Closing MCTSAgent, transposition table saved")

  def __str__(self) -> str:
    """Return a string representation of the agent."""
    return f"MCTSAgent({self.config})"

  def __repr__(self) -> str:
    """Return a detailed string representation of the agent."""
    return f"MCTSAgent(config={self.config!r})"
