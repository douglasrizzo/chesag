import chess

from chesag.agents.minimax import MinimaxAgent
from chesag.position_key import build_position_key


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


def test_default_maxdepth_is_four() -> None:
  agent = MinimaxAgent()

  assert agent.maxdepth == 4


def test_resign_threshold_normalizes_to_negative() -> None:
  agent_positive = MinimaxAgent(resign_threshold=5.0)
  agent_negative = MinimaxAgent(resign_threshold=-5.0)

  assert agent_positive.resign_threshold == -5.0
  assert agent_negative.resign_threshold == -5.0


def test_resign_threshold_none_is_negative_inf() -> None:
  agent = MinimaxAgent(resign_threshold=None)

  assert agent.resign_threshold == float("-inf")


def test_last_search_initialized_as_stats() -> None:
  agent = MinimaxAgent()

  assert agent.last_search.tt_hits == 0
  assert agent.last_search.tt_cutoffs == 0
  assert agent.last_search.depths == {}


def test_get_move_returns_null_when_below_resign_threshold() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/4K1q1 w - - 0 1")
  agent = MinimaxAgent(maxdepth=1, resign_threshold=-5.0)

  move = agent.get_move(board)

  assert move == chess.Move.null()


def test_get_move_returns_only_legal_move() -> None:
  board = chess.Board("8/8/8/8/8/8/4q3/5K1k w - - 0 1")

  assert board.legal_moves.count() == 1

  agent = MinimaxAgent(maxdepth=1)
  move = agent.get_move(board)

  assert move == next(iter(board.legal_moves))


def test_tt_hits_increment_on_repeated_lookups() -> None:
  board = chess.Board()
  agent = MinimaxAgent(maxdepth=2)

  agent.get_move(board)
  first_hits = agent.last_search.tt_hits

  agent.get_move(board)
  second_hits = agent.last_search.tt_hits

  assert second_hits > first_hits or second_hits > 0


def test_negamax_exact_bound_stored_in_tt() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
  agent = MinimaxAgent(maxdepth=2)

  agent.get_move(board)

  key = agent._tt
  assert len(key) > 0


def test_search_stats_exact_root_searched_count() -> None:
  board = chess.Board()
  agent = MinimaxAgent(maxdepth=1)

  agent.get_move(board)

  assert agent.last_search.depth(0).searched == 20


def test_tt_entry_has_exact_bound_and_depth() -> None:
  board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
  agent = MinimaxAgent(maxdepth=2)

  move = agent.get_move(board)
  root_key = agent._tt

  entry = root_key
  assert len(entry) > 0
  root_entry = entry[build_position_key(board)]
  assert root_entry.bound.name == "EXACT"
  assert root_entry.depth == 2
  assert root_entry.best_move == move


def test_tt_entry_has_score() -> None:
  board = chess.Board()
  agent = MinimaxAgent(maxdepth=1)

  agent.get_move(board)

  root_entry = agent._tt[build_position_key(board)]
  assert root_entry.score is not None


def test_negamax_finds_best_move_not_worst() -> None:
  board = chess.Board("6k1/8/8/8/8/8/4q3/3Q2K1 w - - 0 1")
  agent = MinimaxAgent(maxdepth=2)

  move = agent.get_move(board)

  assert move == chess.Move.from_uci("d1e2")


def test_quiescence_stand_pat_equals_beta_returns_early() -> None:
  board = chess.Board("6k1/8/8/8/8/8/4q3/3Q2K1 w - - 0 1")
  agent = MinimaxAgent(maxdepth=1)

  stand_pat = agent.quiescence(board, 1000.0, 1000.0)

  assert stand_pat == 1000.0


def test_quiescence_includes_promotion_moves() -> None:
  board = chess.Board("4k3/7P/8/8/8/8/8/4K3 w - - 0 1")
  agent = MinimaxAgent(maxdepth=1)

  score = agent.quiescence(board, float("-inf"), float("inf"))

  assert score > 8.0
