from collections.abc import Callable

import chess
import pytest
from hypothesis import example, given

from chesag.evaluation import (
  EXTENDED_CENTER,
  bishop_pair_bonus,
  center_control,
  evaluate,
  get_evaluation_stats,
  is_passed_pawn,
  king_safety,
  leaf_evaluate,
  material_balance,
  mobility_score,
  move_bonus,
  mvv_lva_score,
  order_evaluate,
  passed_pawn_score,
  quick_evaluate,
  reset_evaluation_stats,
  rollout_evaluate,
  terminal_evaluation,
)
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


def test_quick_evaluate_matches_order_evaluate() -> None:
  board = chess.Board()

  assert quick_evaluate(board, chess.WHITE) == order_evaluate(board, chess.WHITE)


def test_terminal_evaluation_checkmate_from_perspective() -> None:
  board = chess.Board()
  for san in ["f3", "e5", "g4", "Qh4#"]:
    board.push_san(san)

  assert terminal_evaluation(board, chess.WHITE) == float("-inf")
  assert terminal_evaluation(board, chess.BLACK) == float("inf")


def test_terminal_evaluation_stalemate_is_zero() -> None:
  board = chess.Board("k7/2Q5/8/8/8/8/8/K7 b - - 0 1")

  assert board.is_stalemate()
  assert terminal_evaluation(board, chess.WHITE) == 0.0
  assert terminal_evaluation(board, chess.BLACK) == 0.0


def test_terminal_evaluation_insufficient_material_is_zero() -> None:
  board = chess.Board("8/8/8/4k3/8/8/8/4K3 w - - 0 1")

  assert board.is_insufficient_material()
  assert terminal_evaluation(board, chess.WHITE) == 0.0
  assert terminal_evaluation(board, chess.BLACK) == 0.0


def test_terminal_evaluation_in_progress_is_none() -> None:
  board = chess.Board()

  assert terminal_evaluation(board, chess.WHITE) is None
  assert terminal_evaluation(board, chess.BLACK) is None


def test_evaluation_stats_record_and_reset() -> None:
  reset_evaluation_stats()

  leaf_evaluate(chess.Board(), chess.WHITE)
  leaf_evaluate(chess.Board(), chess.WHITE)
  order_evaluate(chess.Board(), chess.WHITE)

  stats = get_evaluation_stats()
  assert stats.leaf.calls == 2
  assert stats.leaf.total_ns >= 0
  assert stats.order.calls == 1
  assert stats.order.total_ns >= 0
  assert stats.rollout.calls == 0

  reset_evaluation_stats()
  stats = get_evaluation_stats()
  assert stats.leaf.calls == 0
  assert stats.order.calls == 0
  assert stats.rollout.calls == 0


def test_bishop_pair_bonus_requires_two_bishops() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1")

  assert bishop_pair_bonus(board, chess.WHITE) == pytest.approx(0.5)


def test_bishop_pair_bonus_none_for_one_bishop() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1")

  assert bishop_pair_bonus(board, chess.WHITE) == pytest.approx(0.0)


def test_bishop_pair_bonus_perspective_flip() -> None:
  board = chess.Board("2b1kb2/8/8/8/8/8/8/4K3 b - - 0 1")

  assert bishop_pair_bonus(board, chess.BLACK) == pytest.approx(0.5)
  assert bishop_pair_bonus(board, chess.WHITE) == pytest.approx(-0.5)


def test_passed_pawn_score_increases_with_rank() -> None:
  board = chess.Board("4k3/8/8/8/8/4P3/8/4K3 w - - 0 1")
  score_rank3 = passed_pawn_score(board, chess.WHITE)

  board.push_san("e4")
  score_rank4 = passed_pawn_score(board, chess.WHITE)

  assert score_rank4 > score_rank3


def test_is_passed_pawn_true_when_no_enemy_pawns_ahead() -> None:
  board = chess.Board("4k3/8/8/8/8/4P3/8/4K3 w - - 0 1")

  assert is_passed_pawn(board, chess.E3, chess.WHITE)


def test_is_passed_pawn_false_when_blocked() -> None:
  board = chess.Board("4k3/8/8/8/4p3/4P3/8/4K3 w - - 0 1")

  assert not is_passed_pawn(board, chess.E3, chess.WHITE)


def test_is_passed_pawn_false_when_adjacent_enemy_pawn() -> None:
  board = chess.Board("4k3/8/8/8/3p4/4P3/8/4K3 w - - 0 1")

  assert not is_passed_pawn(board, chess.E3, chess.WHITE)


def test_center_control_counts_attackers() -> None:
  board = chess.Board("4k3/8/8/8/8/5N2/8/4K3 w - - 0 1")

  score = center_control(board, chess.WHITE, [chess.D4])
  assert score > 0.0


def test_center_control_perspective_flip() -> None:
  board = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")

  white_score = center_control(board, chess.WHITE, [chess.D4])
  black_score = center_control(board, chess.BLACK, [chess.D4])

  assert white_score == pytest.approx(-black_score)


def test_king_safety_castling_bonus() -> None:
  board = chess.Board("r3k3/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQq - 0 1")

  score = king_safety(board, chess.WHITE)
  assert score > 0.0


def test_king_safety_open_file_penalty() -> None:
  board = chess.Board("3k4/3p4/8/8/8/8/8/4K3 w - - 0 1")

  score = king_safety(board, chess.WHITE)
  assert score < 0.0


def test_mobility_score_perspective_symmetric() -> None:
  board = chess.Board()

  white_score = mobility_score(board, chess.WHITE)
  black_score = mobility_score(board, chess.BLACK)

  assert white_score == pytest.approx(-black_score)


def test_mobility_score_more_moves_is_higher() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")

  score = mobility_score(board, chess.WHITE)
  assert score > 0.0


def test_mvv_lva_score_non_capture_is_zero() -> None:
  board = chess.Board()
  move = chess.Move.from_uci("e2e4")

  assert mvv_lva_score(board, move) == 0.0


def test_mvv_lva_score_capture_prefers_high_victim() -> None:
  board = chess.Board("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
  capture_queen = chess.Move.from_uci("e4d5")

  assert mvv_lva_score(board, capture_queen) > 0.0


def test_mvv_lva_score_en_passant() -> None:
  board = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
  move = chess.Move.from_uci("e5d6")

  assert mvv_lva_score(board, move) > 0.0


def test_move_bonus_capture_and_check() -> None:
  board = chess.Board("4k3/8/8/8/8/8/4q3/3Q2K1 w - - 0 1")
  board.push_san("Qxe2+")

  score = move_bonus(board, chess.WHITE)
  assert score > 0.0


def test_move_bonus_promotion() -> None:
  board = chess.Board("8/3k3P/8/8/8/8/8/4K3 w - - 0 1")
  board.push_san("h8=Q")

  score = move_bonus(board, chess.WHITE)
  assert score == pytest.approx(8.5)


def test_move_bonus_no_moves_is_zero() -> None:
  board = chess.Board()

  assert move_bonus(board, chess.WHITE) == 0.0


def test_evaluate_default_does_not_include_move_bonus() -> None:
  board = chess.Board("4k3/8/8/8/8/8/4q3/3Q2K1 w - - 0 1")
  board.push_san("Qxe2+")

  score_with_defaults = evaluate(board, chess.WHITE)
  score_explicit_false = evaluate(board, chess.WHITE, include_move_bonus=False)

  assert score_with_defaults == score_explicit_false


def test_evaluate_default_includes_material() -> None:
  board = chess.Board()
  board.remove_piece_at(chess.D8)

  score_with_defaults = evaluate(board, chess.WHITE)
  score_without_material = evaluate(board, chess.WHITE, use_material=False)

  assert score_with_defaults != score_without_material


def test_evaluate_default_includes_bishop_pair() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1")

  score_with_defaults = evaluate(board, chess.WHITE)
  score_without_bishop_pair = evaluate(board, chess.WHITE, use_bishop_pair=False)

  assert score_with_defaults != score_without_bishop_pair


def test_evaluate_default_includes_passed_pawns() -> None:
  board = chess.Board("4k3/8/8/8/8/4P3/8/4K3 w - - 0 1")

  score_with_defaults = evaluate(board, chess.WHITE)
  score_without_passed_pawns = evaluate(board, chess.WHITE, use_passed_pawns=False)

  assert score_with_defaults != score_without_passed_pawns


def test_evaluate_default_uses_extended_center() -> None:
  board = chess.Board("4k3/8/8/8/8/5N2/4P3/4K3 w - - 0 1")

  score_with_defaults = evaluate(board, chess.WHITE)
  score_without_center = evaluate(board, chess.WHITE, use_center_extended=False)

  assert score_with_defaults != score_without_center


def test_evaluate_default_includes_king_safety() -> None:
  board = chess.Board("r3k3/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQq - 0 1")

  score_with_defaults = evaluate(board, chess.WHITE)
  score_without_king_safety = evaluate(board, chess.WHITE, use_king_safety=False)

  assert score_with_defaults != score_without_king_safety


def test_evaluate_default_includes_mobility() -> None:
  board = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")

  score_with_defaults = evaluate(board, chess.WHITE)
  score_without_mobility = evaluate(board, chess.WHITE, use_mobility=False)

  assert score_with_defaults != score_without_mobility


def test_evaluate_combines_multiple_components() -> None:
  board = chess.Board("r3k3/pppppppp/8/8/8/5N2/4P3/2B1K2R w KQq - 0 1")

  score = evaluate(board, chess.WHITE)
  material_only = evaluate(
    board,
    chess.WHITE,
    use_bishop_pair=False,
    use_passed_pawns=False,
    use_center_extended=False,
    use_king_safety=False,
    use_mobility=False,
  )

  assert score != material_only


def test_order_evaluate_uses_center_basic_not_extended() -> None:
  board = chess.Board("4k3/8/8/8/8/5N2/4P3/4K3 w - - 0 1")

  order_score = order_evaluate(board, chess.WHITE)
  extended_score = evaluate(board, chess.WHITE, use_center_extended=True, use_center_basic=False)

  assert order_score != extended_score


def test_is_passed_pawn_black_pawn_true() -> None:
  board = chess.Board("4k3/8/8/8/8/3p4/8/4K3 b - - 0 1")

  assert is_passed_pawn(board, chess.D6, chess.BLACK)


def test_is_passed_pawn_black_pawn_false_when_blocked() -> None:
  board = chess.Board("4k3/8/8/8/3P4/3p4/8/4K3 b - - 0 1")

  assert not is_passed_pawn(board, chess.D6, chess.BLACK)


def test_is_passed_pawn_a_file_edge() -> None:
  board = chess.Board("4k3/8/8/8/8/P7/8/4K3 w - - 0 1")

  assert is_passed_pawn(board, chess.A3, chess.WHITE)


def test_is_passed_pawn_h_file_edge() -> None:
  board = chess.Board("4k3/8/8/8/8/7P/8/4K3 w - - 0 1")

  assert is_passed_pawn(board, chess.H3, chess.WHITE)


def test_is_passed_pawn_false_adjacent_on_edge() -> None:
  board = chess.Board("4k3/8/8/8/7p/6P1/8/4K3 w - - 0 1")

  assert not is_passed_pawn(board, chess.G3, chess.WHITE)


def test_rollout_evaluate_excludes_king_safety() -> None:
  board = chess.Board("r3k3/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQq - 0 1")

  rollout_score = rollout_evaluate(board, chess.WHITE)
  full_score = evaluate(board, chess.WHITE)

  assert rollout_score != full_score


def test_rollout_evaluate_includes_terminal() -> None:
  board = chess.Board("k7/2Q5/8/8/8/8/8/K7 b - - 0 1")

  assert rollout_evaluate(board, chess.WHITE) == 0.0


def test_reset_evaluation_stats_zeroes_total_ns() -> None:
  reset_evaluation_stats()

  leaf_evaluate(chess.Board(), chess.WHITE)
  stats_before = get_evaluation_stats()
  assert stats_before.leaf.total_ns > 0

  reset_evaluation_stats()
  stats_after = get_evaluation_stats()
  assert stats_after.leaf.total_ns == 0


def test_get_evaluation_stats_returns_copy() -> None:
  reset_evaluation_stats()
  leaf_evaluate(chess.Board(), chess.WHITE)

  stats1 = get_evaluation_stats()
  stats2 = get_evaluation_stats()
  stats1.leaf.calls = 999

  assert stats2.leaf.calls != 999


def test_evaluate_equals_sum_of_all_enabled_components() -> None:
  board = chess.Board("rn1qk1n1/2pp1ppp/5n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQ - 0 1")

  expected = (
    material_balance(board, chess.WHITE)
    + bishop_pair_bonus(board, chess.WHITE)
    + passed_pawn_score(board, chess.WHITE)
    + center_control(board, chess.WHITE, EXTENDED_CENTER)
    + king_safety(board, chess.WHITE)
    + mobility_score(board, chess.WHITE)
  )

  assert evaluate(board, chess.WHITE) == pytest.approx(expected)


def test_evaluate_move_bonus_included_when_explicitly_enabled() -> None:
  board = chess.Board("4k3/8/8/8/8/8/4q3/3Q2K1 w - - 0 1")
  board.push_san("Qxe2+")

  without_bonus = evaluate(board, chess.WHITE, include_move_bonus=False)
  with_bonus = evaluate(board, chess.WHITE, include_move_bonus=True)

  assert with_bonus != without_bonus
