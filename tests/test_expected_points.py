import math

import pytest

from deepsight.expected_points import (
    BASE_SLOPE,
    Score,
    cp_to_expected_points,
    expected_points_loss,
    mate_to_expected_points,
    rating_slope_scale,
    slope,
)


def test_equal_position_is_half():
    assert cp_to_expected_points(0) == pytest.approx(0.5)


def test_expected_points_are_bounded():
    for cp in (-100000, -5000, -3, 0, 3, 5000, 100000):
        ep = cp_to_expected_points(cp)
        assert 0.0 <= ep <= 1.0


def test_expected_points_are_symmetric():
    for cp in (1, 25, 100, 700, 4000):
        assert cp_to_expected_points(cp) == pytest.approx(1.0 - cp_to_expected_points(-cp))


def test_expected_points_are_monotonic():
    previous = -1.0
    for cp in range(-3000, 3000, 50):
        current = cp_to_expected_points(cp)
        assert current > previous
        previous = current


def test_pawn_up_is_about_sixty_percent():
    assert cp_to_expected_points(100) == pytest.approx(0.591, abs=0.005)


def test_huge_advantage_is_almost_certain():
    assert cp_to_expected_points(2000) > 0.99
    assert cp_to_expected_points(-2000) < 0.01


def test_mate_scores_are_pinned():
    assert mate_to_expected_points(1) == 1.0
    assert mate_to_expected_points(25) == 1.0
    assert mate_to_expected_points(-1) == 0.0
    assert mate_to_expected_points(0) == 0.0


def test_score_prefers_mate_over_centipawns():
    score = Score(cp=1200, mate=4)
    assert score.cp is None
    assert score.is_winning_mate
    assert score.expected_points() == 1.0


def test_score_negation_and_other_side():
    score = Score.from_cp(300)
    assert score.negated().cp == -300

    ep = score.expected_points()
    assert score.expected_points_for_other_side() == pytest.approx(1.0 - ep)

    mate = Score(mate=3)
    assert mate.expected_points_for_other_side() == 0.0
    assert mate.negated().expected_points() == 0.0


def test_score_coercion_accepts_pawns_and_move_evals():
    class DummyEval:
        score_cp = 250.0
        mate = None

    assert Score.coerce(None) is None
    assert Score.coerce(0.25).cp == 25
    assert Score.coerce(DummyEval()).cp == 250
    assert Score.coerce(Score.from_cp(5)).cp == 5
    assert Score.from_move_eval(None) is None


def test_loss_is_never_negative():
    assert expected_points_loss(0.5, 0.4) == pytest.approx(0.1)
    assert expected_points_loss(0.5, 0.7) == 0.0
    assert expected_points_loss(0.5, 0.5) == 0.0
    assert expected_points_loss(None, 0.5) is None
    assert expected_points_loss(0.5, None) is None


def test_rating_makes_the_curve_flatter_for_weaker_players():
    assert rating_slope_scale(None) == 1.0
    assert rating_slope_scale(600) < rating_slope_scale(1500) < rating_slope_scale(2400)
    assert slope(600) < BASE_SLOPE < slope(2400)

    assert cp_to_expected_points(100, rating=800) < cp_to_expected_points(100, rating=2200)


def test_rating_curve_stays_symmetric_and_bounded():
    for rating in (None, 400, 1000, 1500, 2100, 3000):
        for cp in (-3000, -400, 0, 400, 3000):
            ep = cp_to_expected_points(cp, rating=rating)
            assert 0.0 <= ep <= 1.0
            assert ep == pytest.approx(1.0 - cp_to_expected_points(-cp, rating=rating))


def test_lost_position_has_almost_nothing_left_to_lose():
    hopeless = cp_to_expected_points(-600)
    even = cp_to_expected_points(0)

    assert hopeless < 0.11
    assert even - cp_to_expected_points(-250) > 2 * (hopeless - cp_to_expected_points(-1200))


def test_extreme_centipawns_do_not_overflow():
    assert cp_to_expected_points(10 ** 6) == 1.0
    assert cp_to_expected_points(-(10 ** 6)) == 0.0
    assert not math.isnan(cp_to_expected_points(1e9))
