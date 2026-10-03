import chess
import pytest

from deepsight.see import (
    SACRIFICE_THRESHOLD_ADVANCED,
    SACRIFICE_THRESHOLD_BEGINNER,
    SACRIFICE_THRESHOLD_DEFAULT,
    is_sacrifice,
    material_given_up,
    sacrifice_threshold_for_rating,
    static_exchange_evaluation,
)

START = chess.STARTING_FEN


def evaluate(fen, uci):
    return static_exchange_evaluation(chess.Board(fen), chess.Move.from_uci(uci))


def test_quiet_developing_move_is_not_a_trade():
    assert evaluate(START, "g1f3") == 0
    assert evaluate(START, "e2e4") == 0


def test_free_capture_wins_the_piece():
    assert evaluate("4k3/8/8/4n3/8/8/8/4R1K1 w - - 0 1", "e1e5") == 320


def test_recapture_makes_the_move_lose_material():
    assert evaluate("4k3/8/3p4/4n3/8/8/8/4R1K1 w - - 0 1", "e1e5") == -180


def test_exchange_sacrifice_is_negative():
    assert evaluate("4k3/8/8/8/1p6/2n5/8/2R1K3 w - - 0 1", "c1c3") == -180


def test_winning_a_defended_piece_is_still_profitable():
    assert evaluate("4k3/8/2p5/3n4/4P3/8/8/4K3 w - - 0 1", "e4d5") == 220


def test_even_pawn_trade_is_zero():
    assert evaluate("4k3/8/2p5/3p4/4P3/8/8/4K3 w - - 0 1", "e4d5") == 0


def test_hanging_a_piece_is_negative():
    assert evaluate("4k3/8/3p4/8/8/5N2/8/6K1 w - - 0 1", "f3e5") == -320


def test_en_passant_wins_a_pawn():
    assert evaluate("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6") == 100


def test_queen_trade_is_even():
    assert evaluate("4k3/8/2p5/3q4/8/8/8/3QK3 w - - 0 1", "d1d5") == 0


def test_pinned_defender_cannot_recapture():
    board = chess.Board("3k4/8/3b4/4n3/8/6B1/8/3RK3 w - - 0 1")
    assert static_exchange_evaluation(board, chess.Move.from_uci("g3e5")) == 320


def test_illegal_move_is_zero():
    board = chess.Board(START)
    assert static_exchange_evaluation(board, chess.Move.from_uci("e2e5")) == 0


def test_promotion_adds_the_new_queen():
    board = chess.Board("1r4k1/P7/8/8/8/8/8/6K1 w - - 0 1")
    value = static_exchange_evaluation(board, chess.Move.from_uci("a7b8q"))
    assert value == 500 + (900 - 100)


def test_material_given_up_is_never_negative():
    board = chess.Board("4k3/8/8/4n3/8/8/8/4R1K1 w - - 0 1")
    assert material_given_up(board, chess.Move.from_uci("e1e5")) == 0


@pytest.mark.parametrize("rating,threshold", [
    (None, SACRIFICE_THRESHOLD_DEFAULT),
    (800, SACRIFICE_THRESHOLD_BEGINNER),
    (1500, SACRIFICE_THRESHOLD_DEFAULT),
    (2300, SACRIFICE_THRESHOLD_ADVANCED),
])
def test_threshold_follows_rating(rating, threshold):
    assert sacrifice_threshold_for_rating(rating) == threshold


def test_is_sacrifice_respects_the_threshold():
    exchange_sac = (chess.Board("4k3/8/3p4/4n3/8/8/8/4R1K1 w - - 0 1"),
                    chess.Move.from_uci("e1e5"))

    board, move = exchange_sac
    assert is_sacrifice(board, move, threshold=100)
    assert not is_sacrifice(board, move, threshold=300)

    pawn_sac = (chess.Board("4k3/8/3p4/8/8/5N2/8/6K1 w - - 0 1"),
                chess.Move.from_uci("f3e5"))
    assert is_sacrifice(*pawn_sac, threshold=320)


def test_see_does_not_mutate_the_board():
    board = chess.Board("4k3/8/3p4/4n3/8/8/8/4R1K1 w - - 0 1")
    before = board.fen()
    static_exchange_evaluation(board, chess.Move.from_uci("e1e5"))
    assert board.fen() == before
