from collections.abc import Callable

import chess
import pytest
from hypothesis import example, given

from chesag.evaluation import evaluate, leaf_evaluate, material_balance, order_evaluate, rollout_evaluate
from tests.hypothesis_strategies import legal_boards


def test_start_position_evaluates_symmetrically() -> None:
  board = chess.Board()

  assert evaluate(board, chess.WHITE) == pytest.approx(0.0)
  assert evaluate(board, chess.BLACK) == pytest.approx(0.0)


def test_material_balance_flips_by_perspective() -> None:
  board = chess.Board()
  board.remove_piece_at(chess.D8)

  assert material_balance(board, chess.WHITE) == pytest.approx(9.5)
  assert material_balance(board, chess.BLACK) == pytest.approx(-9.5)


def test_checkmate_evaluation_uses_perspective_sign() -> None:
  board = chess.Board()
  for san in ["f3", "e5", "g4", "Qh4#"]:
    board.push_san(san)

  assert board.is_checkmate()
  assert evaluate(board, chess.WHITE) == float("-inf")
  assert evaluate(board, chess.BLACK) == float("inf")


@pytest.mark.parametrize("evaluator", [leaf_evaluate, order_evaluate, rollout_evaluate])
def test_all_eval_tiers_flip_with_perspective(evaluator: Callable[[chess.Board, bool], float]) -> None:
  board = chess.Board("4k3/8/8/8/3Q4/8/8/4K3 b - - 0 1")

  white_score = evaluator(board, chess.WHITE)
  black_score = evaluator(board, chess.BLACK)

  assert white_score == pytest.approx(-black_score)


@given(legal_boards(max_plies=24))
@example(chess.Board())
def test_material_balance_is_perspective_symmetric(board: chess.Board) -> None:
  white_score = material_balance(board, chess.WHITE)
  black_score = material_balance(board, chess.BLACK)

  assert white_score == pytest.approx(-black_score)


@pytest.mark.parametrize("evaluator", [evaluate, leaf_evaluate, order_evaluate, rollout_evaluate])
@given(legal_boards(max_plies=24))
@example(chess.Board())
def test_evaluators_remain_perspective_symmetric(
  evaluator: Callable[[chess.Board, bool], float],
  board: chess.Board,
) -> None:
  white_score = evaluator(board, chess.WHITE)
  black_score = evaluator(board, chess.BLACK)

  assert white_score == pytest.approx(-black_score)
