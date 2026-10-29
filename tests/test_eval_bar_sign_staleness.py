from __future__ import annotations
import chess
import pytest
import time
from deepsight.models.game_state import MoveEval

WHITE_TO_MOVE = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
BLACK_TO_MOVE = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"

@pytest.fixture
def app():
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app

@pytest.fixture
def window(app):
    from deepsight.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()
    app.processEvents()

def _ev(score_cp=None, mate=None, depth=5):
    return MoveEval(move=chess.Move.null(), score_cp=score_cp, mate=mate, depth=depth)


def test_live_update_black_to_move_score_is_negated(window, app):
    window.game_state.load_fen(BLACK_TO_MOVE)
    window._on_live_update(_ev(score_cp=100.0), None, chess.BLACK, BLACK_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._score == -1.0


def test_live_update_white_to_move_score_kept(window, app):
    window.game_state.load_fen(WHITE_TO_MOVE)
    window._on_live_update(_ev(score_cp=100.0), None, chess.WHITE, WHITE_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._score == 1.0


def test_live_update_stale_fen_is_ignored(window, app):
    window.game_state.load_fen(WHITE_TO_MOVE)
    window.eval_bar.set_eval(score_cp=50.0, depth=3)
    window._on_live_update(_ev(score_cp=100.0), None, chess.BLACK, BLACK_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._score == 0.5


def test_live_update_mate_sign_negated_for_black(window, app):
    window.game_state.load_fen(BLACK_TO_MOVE)
    window._on_live_update(_ev(mate=3), None, chess.BLACK, BLACK_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._mate == -3


def test_live_update_stale_mate_is_ignored(window, app):
    window.game_state.load_fen(WHITE_TO_MOVE)
    window.eval_bar.set_eval(mate=1, depth=0)
    window._on_live_update(_ev(mate=3), None, chess.BLACK, BLACK_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._mate == 1


def test_quick_eval_black_to_move_score_negated(window, app):
    window.game_state.load_fen(BLACK_TO_MOVE)
    window.quick_eval = object()
    window._on_quick_eval(_ev(score_cp=100.0), None, chess.BLACK, BLACK_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._score == -1.0


def test_quick_eval_stale_fen_is_ignored(window, app):
    window.game_state.load_fen(WHITE_TO_MOVE)
    window.eval_bar.set_eval(score_cp=50.0, depth=3)
    window.quick_eval = object()
    window._on_quick_eval(_ev(score_cp=100.0), None, chess.BLACK, BLACK_TO_MOVE)
    app.processEvents()
    assert window.eval_bar._score == 0.5


class _FakeEngine:
    def __init__(self):
        from deepsight.engine_manager import EngineManager
        self._real = EngineManager("dummy-engine")
        self.stdout_buffer: list[str] = []
        self.written: list[str] = []

    def get_output(self) -> list[str]:
        out = list(self.stdout_buffer)
        self.stdout_buffer.clear()
        return out

    def parse_uci_info(self, line: str):
        return self._real.parse_uci_info(line)


def _make_qe(app) -> "QuickEvaluator":
    from deepsight.quick_evaluator import QuickEvaluator
    from deepsight.engine_manager import EngineProtocol

    qe = QuickEvaluator("dummy-engine", EngineProtocol.UCI, movetime_ms=1000)
    qe._engine = _FakeEngine()
    qe._running = True
    qe._generation = 1
    qe._running_generation = 1
    qe._infinite = True
    qe._board_turn = chess.WHITE
    qe._fen = WHITE_TO_MOVE
    qe._start_time = time.time()
    return qe


def test_quick_eval_poll_discards_stale_output_after_restart(app):
    qe = _make_qe(app)
    qe._discard_polls = 3

    emitted = []
    qe.eval_ready.connect(lambda ev, bm, side, fen: emitted.append((ev, side, fen)))

    qe._engine.stdout_buffer = ["info depth 10 score cp 100 pv e2e4", "bestmove e2e4"]
    qe._poll()
    app.processEvents()

    assert emitted == []
    assert qe._discard_polls == 2


def test_quick_eval_poll_processes_fresh_output_after_discards(app):
    qe = _make_qe(app)
    qe._discard_polls = 0

    received = []
    qe.eval_ready.connect(lambda ev, bm, side, fen: received.append((ev.score_cp, side, fen)))

    qe._engine.stdout_buffer = ["info depth 10 score cp 50 pv d2d4"]
    qe._poll()
    app.processEvents()

    assert len(received) == 1
    assert received[0] == (50, chess.WHITE, WHITE_TO_MOVE)


def test_quick_eval_poll_discard_decrements_per_cycle(app):
    qe = _make_qe(app)
    qe._discard_polls = 2

    emitted = []
    qe.eval_ready.connect(lambda ev, bm, side, fen: emitted.append(ev))

    qe._engine.stdout_buffer = ["info depth 10 score cp 100 pv e2e4"]
    qe._poll()
    qe._engine.stdout_buffer = ["info depth 11 score cp 200 pv d2d4"]
    qe._poll()
    app.processEvents()
    assert emitted == []
    assert qe._discard_polls == 0

    received = []
    qe.eval_ready.disconnect()
    qe.eval_ready.connect(lambda ev, bm, side, fen: received.append(ev.score_cp))
    qe._engine.stdout_buffer = ["info depth 10 score cp 75 pv d2d4"]
    qe._poll()
    app.processEvents()
    assert received == [75]

