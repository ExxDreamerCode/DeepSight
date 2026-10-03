import os
import sys
import time
from pathlib import Path

import pytest

from deepsight.analysis_engine import AnalysisEngine
from deepsight.classification_types import ClassificationConfig, MoveClassification
from deepsight.engine_manager import EngineProtocol
from deepsight.models.game_state import GameState
from deepsight.move_classifier import BookChecker, MoveClassifier

ROOT = Path(__file__).resolve().parent.parent

PGN = """[Event "Paris"]

1. e4 e5 2. f4 exf4 3. Bc4 Qh4+ 4. Kf1 b5 5. Bxb5 Nf6 6. Nf3 Qh6
7. d3 Nh5 8. Nh4 Qg5 9. Nf5 c6 10. g4 Nf6 11. Rg1 cxb5 12. h4 Qg6
13. h5 Qg5 14. Qf3 Ng8 15. Bxf4 Qf6 16. Nc3 Bc5 17. Nd5 Qxb2 18. Bd6 Bxg1
19. e5 Qxa1+ 20. Ke2 Na6 21. Nxg7+ Kd8 22. Qf6+ Nxf6 23. Be7# *
"""

ENGINE_CANDIDATES = (
    "Engines/ember-1.3.1.exe",
    "Engines/stockfish-windows-x86-64.exe",
    "Engines/ember.exe",
    "Engines/stockfish.exe",
)


def find_engine():
    for candidate in ENGINE_CANDIDATES:
        path = ROOT / candidate
        if path.is_file():
            return str(path)
    return None


pytestmark = pytest.mark.skipif(
    os.environ.get("DEEPSIGHT_RUN_ENGINE_TESTS") != "1" or find_engine() is None,
    reason="set DEEPSIGHT_RUN_ENGINE_TESTS=1 and provide an engine binary",
)


@pytest.fixture
def qt_app():
    from PyQt6.QtCore import QCoreApplication

    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    yield app


def analyse(pgn, time_per_move=120, timeout=240, game_state=None, **settings):
    if game_state is None:
        game_state = GameState()
        assert game_state.load_pgn(pgn), "test PGN must parse"

    classifier = MoveClassifier(
        book_checker=BookChecker(str(ROOT / "Books")),
        config=ClassificationConfig(),
    )
    analysis = AnalysisEngine(game_state, find_engine(), EngineProtocol.UCI, classifier)
    analysis.time_per_move = time_per_move
    analysis.multipv = settings.pop("multipv", 3)
    for name, value in settings.items():
        setattr(analysis, name, value)

    analysed = []
    errors = []
    analysis.move_analyzed.connect(analysed.append)
    analysis.analysis_error.connect(errors.append)
    analysis.start_analysis()

    deadline = time.time() + timeout
    while analysis._running and time.time() < deadline:
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        time.sleep(0.01)

    from PyQt6.QtCore import QCoreApplication
    for _ in range(5):
        QCoreApplication.processEvents()
        time.sleep(0.01)

    analysis.stop()
    assert not errors, errors
    return analysed, analysis, game_state


def test_full_game_analysis_produces_labels(qt_app):
    analysed, _, _ = analyse(PGN)

    assert analysed, "no move was analysed"

    valid = {label.value for label in MoveClassification} | {"Unknown"}
    labels = {move.classification for move in analysed}
    assert labels <= valid, f"unexpected labels: {labels - valid}"

    graded = [move for move in analysed if move.classification != "Unknown"]
    assert graded
    assert all(move.ep_loss is not None for move in graded)
    assert all(0.0 <= move.ep_loss <= 1.0 for move in graded)

    assert len(labels) >= 4, f"too few distinct labels: {labels}"


def test_full_game_finds_sacrifices_and_forced_moves(qt_app):
    analysed, _, _ = analyse(PGN)
    by_san = {}
    for move in analysed:
        by_san.setdefault(move.san, move)

    queen_sacrifice = by_san.get("Qf6+")
    assert queen_sacrifice is not None, [m.san for m in analysed]
    assert queen_sacrifice.is_sacrifice
    assert queen_sacrifice.see == -580

    forced = by_san.get("Kd8")
    assert forced is not None
    assert forced.classification == MoveClassification.FORCED.value


def test_multi_pv_alternatives_are_collected(qt_app):
    analysed, _, _ = analyse(PGN, time_per_move=150)
    with_alternatives = [move for move in analysed if move.alternatives]

    assert with_alternatives, "MultiPV produced no alternative lines"
    best = with_alternatives[-1]
    assert len(best.alternatives) <= 2
    assert all(ev.multipv >= 2 for ev in best.alternatives)


def test_second_run_reuses_results_and_scores_only_the_new_tail(qt_app):
    analysed, analysis, game_state = analyse(PGN, time_per_move=120)
    total = len(game_state.moves)
    assert total > 2
    assert analysis.analyzed_move_count == total

    before = [move.analysis_signature for move in game_state.moves]
    before_labels = [move.classification for move in game_state.moves]
    assert all(before)

    analysed, analysis, game_state = analyse(PGN, time_per_move=120, game_state=game_state)

    assert analysis.analyzed_move_count == 0
    assert analysis.skipped_move_count == total
    assert [move.analysis_signature for move in game_state.moves] == before
    assert len(analysed) == total, "skipped moves must still be reported to the interface"

    game_state.go_to_move(total - 2)
    played = game_state.moves[-1].move
    replacement = next(m for m in game_state.board.legal_moves if m != played)
    assert game_state.make_move(replacement) is not None
    assert len(game_state.moves) == total
    assert not game_state.moves[-1].has_analysis()

    analysed, analysis, game_state = analyse(PGN, time_per_move=120, game_state=game_state)

    assert analysis.analyzed_move_count == 1, "only the edited move may be searched again"
    assert analysis.skipped_move_count == total - 1
    assert game_state.moves[-1].has_analysis()
    assert [m.analysis_signature for m in game_state.moves[:-1]] == before[:-1]
    assert [m.classification for m in game_state.moves[:-1]] == before_labels[:-1]
