import chess

from chesag.agents.minimax import MinimaxAgent


def test_minimax_returns_legal_move_from_start_position() -> None:
  board = chess.Board()
  agent = MinimaxAgent(maxdepth=1)

  move = agent.get_move(board)

  assert move in board.legal_moves
