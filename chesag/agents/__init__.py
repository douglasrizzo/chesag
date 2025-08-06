from .base import BaseAgent as BaseAgent
from .mcts.agent import MCTSAgent as MCTSAgent
from .minimax import MinimaxAgent as MinimaxAgent
from .random import RandomAgent as RandomAgent
from .stockfish import StockfishAgent as StockfishAgent

# provide a dictionary of agents
AGENTS = {
  "random": RandomAgent,
  "minimax": MinimaxAgent,
  "mcts": MCTSAgent,
  "base": BaseAgent,
  "stockfish": StockfishAgent,
}
