import chess

from chesag.agents.mcts.agent import MCTSAgent, MCTSConfig
from chesag.agents.mcts.algorithm import MCTSSearcher

ONE_MOVE_FEN = "rnb1kbnr/p1p2ppp/1p2p3/3p4/4PP2/1P4qP/P1PP4/RNBQKBNR w KQkq - 0 6"


def test_mcts_searcher_returns_for_single_legal_move() -> None:
  board = chess.Board(ONE_MOVE_FEN)

  move_and_eval = MCTSSearcher.should_return_single_move(board)

  assert move_and_eval is not None
  assert move_and_eval[0] == chess.Move.from_uci("e1e2")


def test_mcts_agent_returns_legal_move_from_start_position() -> None:
  board = chess.Board()
  agent = MCTSAgent(MCTSConfig(num_simulations=5, parallel=False, use_pruning=False))

  move = agent.get_move(board)

  assert move in board.legal_moves
