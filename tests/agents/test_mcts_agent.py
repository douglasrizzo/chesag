import chess
import pytest

from chesag.agents.mcts.agent import MCTSAgent, MCTSConfig
from chesag.agents.mcts.algorithm import MCTSSearcher
from chesag.agents.mcts.node import Node
from chesag.move_priority import HeuristicMovePrioritizer
from chesag.position_key import build_position_key

ONE_MOVE_FEN = "rnb1kbnr/p1p2ppp/1p2p3/3p4/4PP2/1P4qP/P1PP4/RNBQKBNR w KQkq - 0 6"


def test_mcts_searcher_returns_for_single_legal_move() -> None:
  board = chess.Board(ONE_MOVE_FEN)

  move_and_eval = MCTSSearcher.should_return_single_move(board)

  assert move_and_eval is not None
  assert move_and_eval[0] == chess.Move.from_uci("e1e2")


def test_mcts_agent_returns_legal_move_from_start_position() -> None:
  board = chess.Board()
  agent = MCTSAgent(MCTSConfig(num_simulations=5, use_transposition_table=False))

  move = agent.get_move(board)

  assert move in board.legal_moves


def test_expand_returns_the_newly_added_child() -> None:
  board = chess.Board()
  node = Node(board=board, move_prioritizer=HeuristicMovePrioritizer())

  child = node.expand()

  assert child is not None
  assert child is node.children[0]
  assert child.move is not None
  assert child.move in board.legal_moves


def test_select_child_prefers_higher_prior_when_unvisited() -> None:
  board = chess.Board()
  prioritizer = HeuristicMovePrioritizer()
  root = Node(board=board, move_prioritizer=prioritizer)
  high_prior = Node(parent=root, move=chess.Move.from_uci("e2e4"), move_prioritizer=prioritizer, prior=0.9)
  low_prior = Node(parent=root, move=chess.Move.from_uci("a2a3"), move_prioritizer=prioritizer, prior=0.1)
  root.children = [low_prior, high_prior]
  root.visits = 10

  selected = root.select_child(c_puct=1.4)

  assert selected is high_prior


def test_config_uses_honest_transposition_table_flag() -> None:
  with pytest.warns(DeprecationWarning):
    config = MCTSConfig(num_simulations=5, use_pruning=False)

  assert config.use_transposition_table is False


def test_config_string_shows_only_live_knobs() -> None:
  config = MCTSConfig(num_simulations=7, c_puct=2.5, use_transposition_table=False)

  assert str(config) == "sims=7, c_puct=2.5, tt=False"


def test_removed_knobs_are_deprecated_not_broken() -> None:
  with pytest.warns(DeprecationWarning):
    config = MCTSConfig(parallel=False, num_workers=2, rollouts_per_leaf=4)

  assert config.use_transposition_table is True


def test_agent_deprecates_removed_knobs() -> None:
  with pytest.warns(DeprecationWarning):
    agent = MCTSAgent(parallel=False, num_workers=2, rollouts_per_leaf=4)

  assert agent.config.use_transposition_table is True


def test_mcts_transposition_table_uses_position_keys() -> None:
  board = chess.Board()
  searcher = MCTSSearcher(use_transposition_table=True)
  node = Node(board=board, move_prioritizer=searcher.move_prioritizer)

  result = searcher.simulate(node)

  assert isinstance(result, float)
  assert searcher.transposition_table is not None
  assert build_position_key(board) in searcher.transposition_table
