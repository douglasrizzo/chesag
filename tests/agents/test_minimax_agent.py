import chess

from chesag.agents.minimax import MinimaxAgent


def test_minimax_returns_legal_move_from_start_position() -> None:
  board = chess.Board()
  agent = MinimaxAgent(maxdepth=1)

  move = agent.get_move(board)

  assert move in board.legal_moves


def test_minimax_finds_white_mate_in_one() -> None:
  board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
  agent = MinimaxAgent(maxdepth=2)

  move = agent.get_move(board)

  assert move == chess.Move.from_uci("h5f7")


def test_minimax_finds_black_mate_in_one() -> None:
  board = chess.Board()
  for san in ("f3", "e5", "g4"):
    board.push_san(san)
  agent = MinimaxAgent(maxdepth=2)

  move = agent.get_move(board)

  assert move == chess.Move.from_uci("d8h4")


def test_transposition_table_records_hits_on_repeated_search() -> None:
  board = chess.Board()
  agent = MinimaxAgent(maxdepth=3)

  first_move = agent.get_move(board)
  first_tt_size = len(agent._tt)

  second_move = agent.get_move(board)

  assert second_move == first_move
  assert len(agent._tt) >= first_tt_size
  assert agent.last_search.tt_hits > 0


def test_quiescence_prefers_winning_capture() -> None:
  board = chess.Board("6k1/8/8/8/8/8/4q3/3Q2K1 w - - 0 1")
  agent = MinimaxAgent(maxdepth=1)

  score = agent.quiescence(board, float("-inf"), float("inf"))

  assert score > 8.0
