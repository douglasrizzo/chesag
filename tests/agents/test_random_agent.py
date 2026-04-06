import chess

from chesag.agents.random import RandomAgent


def test_random_agent_returns_legal_move_from_start_position() -> None:
  board = chess.Board()
  agent = RandomAgent(seed=0)

  move = agent.get_move(board)

  assert move in board.legal_moves
