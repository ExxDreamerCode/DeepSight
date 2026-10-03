import math
from pathlib import Path

import chess
import pytest

from deepsight.classification_types import (
    ClassificationConfig,
    MoveClassification,
    is_endgame_position,
)
from deepsight.expected_points import Score, slope
from deepsight.move_classifier import BookChecker, MoveClassifier
from deepsight.models.game_state import MoveEval

START = chess.STARTING_FEN

GREEK_GIFT = "r1bq1rk1/pppn1ppp/3b1n2/3pp3/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 1"

ENDGAME_SAC = "4k3/8/3p4/4p3/8/4R3/8/4K3 w - - 0 1"

FORCED_MOVE = "6bk/8/8/8/8/8/8/Kr6 w - - 0 1"


def make_classifier(**overrides) -> MoveClassifier:
    config = ClassificationConfig(use_book=overrides.pop("use_book", False), **overrides)
    return MoveClassifier(book_checker=BookChecker("does-not-exist"), config=config)


def score_for_ep(ep: float, rating=None) -> Score:
    ep = min(max(ep, 1e-6), 1 - 1e-6)
    return Score.from_cp(math.log(ep / (1 - ep)) / slope(rating))


def score_after_for_loss(ep_before: float, loss: float, rating=None) -> Score:
    target = ep_before - loss
    return score_for_ep(1.0 - target, rating=rating)


def classify(played: str, best: str, before: Score, after: Score,
             classifier: MoveClassifier = None, fen: str = START,
             alternatives=None, prev_player_ep=None):
    classifier = classifier or make_classifier()
    board = chess.Board(fen)
    return classifier.classify(
        board_before=board,
        played_move=chess.Move.from_uci(played),
        best_move=chess.Move.from_uci(best) if best else None,
        eval_before=before,
        eval_after=after,
        alternatives=alternatives,
        prev_player_ep=prev_player_ep,
    )


@pytest.mark.parametrize("loss,expected", [
    (0.0, MoveClassification.BEST.value),
    (0.005, MoveClassification.EXCELLENT.value),
    (0.018, MoveClassification.EXCELLENT.value),
    (0.022, MoveClassification.GOOD.value),
    (0.048, MoveClassification.GOOD.value),
    (0.052, MoveClassification.INACCURACY.value),
    (0.098, MoveClassification.INACCURACY.value),
    (0.102, MoveClassification.MISTAKE.value),
    (0.198, MoveClassification.MISTAKE.value),
    (0.202, MoveClassification.BLUNDER.value),
    (0.50, MoveClassification.BLUNDER.value),
])
def test_expected_point_bands(loss, expected):
    ep_before = 0.5
    result = classify("g1f3", "e2e4",
                      score_for_ep(ep_before),
                      score_after_for_loss(ep_before, loss))
    assert result.label == expected, result.reason


def test_playing_the_engine_move_is_best():
    result = classify("g1f3", "g1f3", Score.from_cp(20), Score.from_cp(-20))
    assert result.label == MoveClassification.BEST.value
    assert result.is_best
    assert result.ep_loss == pytest.approx(0.0, abs=1e-9)


def test_loss_never_goes_negative_when_engine_reevaluates():
    result = classify("g1f3", "g1f3", Score.from_cp(20), Score.from_cp(-400))
    assert result.label == MoveClassification.BEST.value
    assert result.ep_loss == 0.0


def test_hopeless_position_turns_blunder_into_inaccuracy():
    result = classify("g1f3", "e2e4", Score.from_cp(-600), Score.from_cp(1100))

    assert result.label == MoveClassification.INACCURACY.value
    assert result.ep_loss is not None and result.ep_loss < 0.10


def test_hopeless_position_can_even_be_a_good_move():
    result = classify("g1f3", "e2e4", Score.from_cp(-1000), Score.from_cp(2000))

    assert result.label == MoveClassification.GOOD.value
    assert result.ep_loss < 0.05


def test_equal_position_punishes_the_same_material_loss():
    result = classify("g1f3", "e2e4", Score.from_cp(20), Score.from_cp(250))
    assert result.label == MoveClassification.BLUNDER.value


def test_winning_position_is_forgiving_about_material():
    comfortable = classify("g1f3", "e2e4", Score.from_cp(800), Score.from_cp(-500))
    assert comfortable.label in (MoveClassification.BEST.value,
                                 MoveClassification.EXCELLENT.value,
                                 MoveClassification.GOOD.value,
                                 MoveClassification.INACCURACY.value)

    fatal = classify("g1f3", "e2e4", Score.from_cp(100), Score.from_cp(200))
    assert fatal.label == MoveClassification.BLUNDER.value
    assert fatal.ep_loss > comfortable.ep_loss


def test_losing_player_gaining_material_is_labelled_well():
    result = classify("g1f3", "e2e4", Score.from_cp(-800), Score.from_cp(400))
    assert result.label in (MoveClassification.BEST.value, MoveClassification.EXCELLENT.value)


def test_delivering_checkmate_is_best():
    result = classify("a1a8", "a1a8", Score(mate=1), Score(mate=0),
                      fen="6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    assert result.label == MoveClassification.BEST.value
    assert result.reason == "checkmate"


def test_missing_a_forced_mate_is_a_miss():
    result = classify("h2h3", "a1a8", Score(mate=1), Score.from_cp(-900),
                      fen="6k1/5ppp/8/8/8/8/7P/R6K w - - 0 1")
    assert result.label == MoveClassification.MISS.value
    assert "mate" in result.reason


def test_keeping_the_mate_alive_is_not_a_miss():
    result = classify("a1a8", "a1a8", Score(mate=1), Score(mate=-5),
                      fen="6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    assert result.label == MoveClassification.BEST.value


def test_throwing_away_a_winning_position_is_a_miss():
    ep_before = 0.85
    result = classify("g1f3", "e2e4",
                      score_for_ep(ep_before),
                      score_after_for_loss(ep_before, 0.35))
    assert result.label == MoveClassification.MISS.value
    assert "winning continuation" in result.reason


def test_being_mated_is_not_punished_as_a_blunder():
    result = classify("g1f3", "e2e4", Score(mate=-2), Score(mate=8))
    assert result.label in (MoveClassification.BEST.value, MoveClassification.EXCELLENT.value)


def test_single_legal_move_is_forced():
    board = chess.Board(FORCED_MOVE)
    assert board.legal_moves.count() == 1

    result = classify("a1b1", "a1b1", Score.from_cp(-300), Score.from_cp(320),
                      fen=FORCED_MOVE)
    assert result.label == MoveClassification.FORCED.value


def test_forced_label_can_be_disabled():
    classifier = make_classifier(mark_forced_moves=False)
    result = classify("a1b1", "a1b1", Score.from_cp(-300), Score.from_cp(300),
                      classifier=classifier, fen=FORCED_MOVE)
    assert result.label == MoveClassification.BEST.value


def test_book_move_is_recognised(tmp_path):
    book = tmp_path / "opening.txt"
    book.write_text(f"{START}|g1f3\n", encoding="utf-8")

    classifier = MoveClassifier(book_checker=BookChecker(str(tmp_path)))
    result = classify("g1f3", "g1f3", Score.from_cp(20), Score.from_cp(-20),
                      classifier=classifier)
    assert result.label == MoveClassification.BOOK.value


def test_non_book_move_is_graded(tmp_path):
    (tmp_path / "opening.txt").write_text(f"{START}|e2e4\n", encoding="utf-8")

    classifier = MoveClassifier(book_checker=BookChecker(str(tmp_path)))
    result = classify("g1f3", "g1f3", Score.from_cp(20), Score.from_cp(-20),
                      classifier=classifier)
    assert result.label == MoveClassification.BEST.value


def test_greek_gift_is_brilliant():
    classifier = make_classifier(sacrifice_cp=200)
    result = classify(
        "d3h7", "d3h7",
        Score.from_cp(100), Score.from_cp(-100),
        classifier=classifier, fen=GREEK_GIFT,
        alternatives=[(chess.Move.from_uci("a2a3"), Score.from_cp(60))],
    )

    assert result.label == MoveClassification.BRILLIANT.value
    assert result.is_sacrifice
    assert result.see == -230


def test_sacrifice_without_multipv_data_is_not_brilliant():
    result = classify("d3h7", "d3h7", Score.from_cp(100), Score.from_cp(-100),
                      fen=GREEK_GIFT)
    assert result.label == MoveClassification.BEST.value
    assert result.is_sacrifice


def test_brilliant_needs_a_bad_position_guard():
    classifier = make_classifier(sacrifice_cp=200)
    result = classify(
        "d3h7", "d3h7",
        Score.from_cp(100), Score.from_cp(700),
        classifier=classifier, fen=GREEK_GIFT,
        alternatives=[(chess.Move.from_uci("a2a3"), Score.from_cp(60))],
    )
    assert result.label != MoveClassification.BRILLIANT.value


def test_brilliant_needs_a_choice():
    classifier = make_classifier(sacrifice_cp=200)
    result = classify(
        "d3h7", "d3h7",
        Score.from_cp(100), Score.from_cp(-100),
        classifier=classifier, fen=GREEK_GIFT,
        alternatives=[
            (chess.Move.from_uci("a2a3"), Score.from_cp(-400)),
            (chess.Move.from_uci("h2h3"), Score.from_cp(-500)),
        ],
    )
    assert result.label == MoveClassification.GREAT.value
    assert result.only_good_move


def test_brilliant_is_not_awarded_when_already_completely_winning():
    classifier = make_classifier(sacrifice_cp=200)
    result = classify(
        "d3h7", "d3h7",
        Score.from_cp(100), Score.from_cp(-100),
        classifier=classifier, fen=GREEK_GIFT,
        alternatives=[
            (chess.Move.from_uci("a2a3"), Score.from_cp(900)),
            (chess.Move.from_uci("h2h3"), Score.from_cp(850)),
        ],
    )
    assert result.label == MoveClassification.BEST.value


def test_endgame_sacrifice_must_be_the_only_good_move():
    classifier = make_classifier(sacrifice_cp=200)
    board = chess.Board(ENDGAME_SAC)
    assert is_endgame_position(board)

    brilliant = classify(
        "e3e5", "e3e5",
        Score.from_cp(50), Score.from_cp(-50),
        classifier=classifier, fen=ENDGAME_SAC,
        alternatives=[
            (chess.Move.from_uci("e3e2"), Score.from_cp(-200)),
            (chess.Move.from_uci("e3a3"), Score.from_cp(-150)),
        ],
    )
    assert brilliant.label == MoveClassification.BRILLIANT.value

    guarded = classify(
        "e3e5", "e3e5",
        Score.from_cp(50), Score.from_cp(-50),
        classifier=classifier, fen=ENDGAME_SAC,
        alternatives=[(chess.Move.from_uci("e3e2"), Score.from_cp(40))],
    )
    assert guarded.label != MoveClassification.BRILLIANT.value


def test_a_move_that_wins_material_is_never_brilliant():
    classifier = make_classifier(sacrifice_cp=200)
    result = classify(
        "d3h7", "d3h7",
        Score.from_cp(100), Score.from_cp(-100),
        classifier=classifier, fen=GREEK_GIFT,
        alternatives=[(chess.Move.from_uci("a2a3"), Score.from_cp(60))],
    )
    assert result.is_sacrifice

    quiet = classify(
        "a2a3", "d3h7",
        Score.from_cp(100), Score.from_cp(-40),
        classifier=classifier, fen=GREEK_GIFT,
        alternatives=[(chess.Move.from_uci("h2h3"), Score.from_cp(60))],
    )
    assert quiet.label != MoveClassification.BRILLIANT.value


def test_rating_changes_what_counts_as_a_sacrifice():
    pawn_sac = [(chess.Move.from_uci("a2a3"), Score.from_cp(60))]
    beginner = make_classifier(rating=800)
    assert beginner.config.sacrifice_threshold() == 100
    assert make_classifier(rating=2300).config.sacrifice_threshold() == 300

    result = classify("d3h7", "d3h7", Score.from_cp(100), Score.from_cp(-100),
                      classifier=beginner, fen=GREEK_GIFT, alternatives=pawn_sac)
    assert result.label == MoveClassification.BRILLIANT.value


def test_only_good_move_is_great():
    result = classify(
        "g1f3", "g1f3", Score.from_cp(0), Score.from_cp(0),
        alternatives=[
            (chess.Move.from_uci("e2e4"), Score.from_cp(-150)),
            (chess.Move.from_uci("d2d4"), Score.from_cp(-250)),
        ],
    )
    assert result.label == MoveClassification.GREAT.value
    assert result.only_good_move
    assert result.reason == "only good move in the position"


def test_a_good_alternative_prevents_great():
    result = classify(
        "g1f3", "g1f3", Score.from_cp(0), Score.from_cp(0),
        alternatives=[(chess.Move.from_uci("e2e4"), Score.from_cp(-5))],
    )
    assert result.label == MoveClassification.BEST.value
    assert not result.only_good_move


def test_great_does_not_fire_in_a_dead_lost_position():
    ep_before = 0.02
    result = classify(
        "g1f3", "g1f3",
        score_for_ep(ep_before), score_after_for_loss(ep_before, 0.0),
        alternatives=[(chess.Move.from_uci("e2e4"), Score.from_cp(-1500))],
    )
    assert result.label != MoveClassification.GREAT.value


def test_turning_a_losing_position_into_an_equal_one_is_great():
    ep = 0.55
    result = classify(
        "g1f3", "g1f3",
        score_for_ep(ep), score_after_for_loss(ep, 0.0),
        prev_player_ep=0.10,
    )
    assert result.label == MoveClassification.GREAT.value
    assert "losing position" in result.reason


def test_turning_an_equal_position_into_a_winning_one_is_great():
    ep = 0.85
    result = classify(
        "g1f3", "g1f3",
        score_for_ep(ep), score_after_for_loss(ep, 0.0),
        prev_player_ep=0.50,
    )
    assert result.label == MoveClassification.GREAT.value
    assert "equal position" in result.reason


def test_quiet_move_from_an_equal_position_is_not_great():
    ep = 0.55
    result = classify(
        "g1f3", "g1f3",
        score_for_ep(ep), score_after_for_loss(ep, 0.0),
        prev_player_ep=0.50,
    )
    assert result.label == MoveClassification.BEST.value


def test_accepts_legacy_pawn_floats():
    result = classify("g1f3", "g1f3", 0.2, -0.2)
    assert result.label == MoveClassification.BEST.value
    assert result.ep_loss == pytest.approx(0.0, abs=1e-6)


def test_accepts_move_eval_objects():
    before = MoveEval(move=chess.Move.from_uci("g1f3"), score_cp=20.0, depth=18)
    after = MoveEval(move=chess.Move.null(), score_cp=-20.0, depth=18)

    result = classify("g1f3", "g1f3", before, after)
    assert result.label == MoveClassification.BEST.value


def test_accepts_move_eval_alternatives():
    result = classify(
        "g1f3", "g1f3", Score.from_cp(0), Score.from_cp(0),
        alternatives=[MoveEval(move=chess.Move.from_uci("e2e4"), score_cp=-200.0)],
    )
    assert result.only_good_move
    assert result.label == MoveClassification.GREAT.value


def test_alternatives_are_annotated_with_ep_and_see():
    result = classify(
        "g1f3", "g1f3", Score.from_cp(0), Score.from_cp(0),
        alternatives=[(chess.Move.from_uci("e2e4"), Score.from_cp(-200))],
    )
    line = result.alternatives[0]
    assert line.ep is not None and line.ep_loss is not None
    assert line.see == 0


def test_missing_multi_pv_line_is_skipped():
    result = classify(
        "g1f3", "g1f3", Score.from_cp(0), Score.from_cp(0),
        alternatives=[None, (chess.Move.null(), Score.from_cp(0)),
                      (chess.Move.from_uci("e2e4"), Score.from_cp(-200))],
    )
    assert len(result.alternatives) == 1


def test_missing_evaluation_falls_back_gracefully():
    best = classify("g1f3", "g1f3", None, None)
    assert best.label == MoveClassification.BEST.value

    no_best = classify("g1f3", "", None, None)
    assert no_best.label == MoveClassification.EXCELLENT.value

    worse = classify("g1f3", "e2e4", None, None)
    assert worse.label == MoveClassification.GOOD.value


def test_result_metadata_is_populated():
    result = classify("d3h7", "d3h7", Score.from_cp(100), Score.from_cp(-100),
                      classifier=make_classifier(sacrifice_cp=200), fen=GREEK_GIFT,
                      alternatives=[(chess.Move.from_uci("a2a3"), Score.from_cp(60))])

    assert result.is_positive
    assert not result.is_negative
    assert str(result) == result.label
    assert result.ep_before == pytest.approx(result.ep_after)
    assert result.ep_loss == pytest.approx(0.0, abs=1e-9)
    assert result.only_good_move is False


def test_negative_labels_are_flagged():
    result = classify("g1f3", "e2e4", Score.from_cp(0), Score.from_cp(600))
    assert result.is_negative
    assert not result.is_positive


def test_illegal_played_move_does_not_crash():
    result = classify("e2e5", "g1f3", Score.from_cp(0), Score.from_cp(0))
    assert result.label
    assert result.see is None


def test_every_label_has_an_icon():
    icons = Path(__file__).resolve().parent.parent / "Images" / "Moves"
    if not icons.is_dir():
        pytest.skip("icon directory not available")

    names = {path.stem for path in icons.glob("*.svg")}
    missing = {label.value for label in MoveClassification} - names
    assert not missing, f"missing icons: {sorted(missing)}"


@pytest.mark.parametrize("label", [label.value for label in MoveClassification])
def test_labels_are_plain_strings(label):
    assert label == str(label)
    assert isinstance(MoveClassification(label), str)
