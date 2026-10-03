from __future__ import annotations

import chess
import pytest

from deepsight.analysis_engine import AnalysisEngine
from deepsight.engine_manager import EngineManager, EngineProtocol
from deepsight.models.game_state import GameState
from deepsight.move_classifier import MoveClassifier

PGN = """
[Event "Short"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
"""


class FakeEngine:

    parse_uci_info = EngineManager.parse_uci_info

    def __init__(self, engine_path: str = "fake-engine"):
        self.engine_path = engine_path
        self.searches = []
        self.multipv = 1
        self.started = False
        self._board = chess.Board()
        self._pending = []

    def start(self) -> bool:
        self.started = True
        return True

    def stop(self):
        self.started = False

    def set_multipv(self, count: int):
        self.multipv = count

    def set_position(self, board: chess.Board):
        self._board = board.copy(stack=False)

    def start_analysis(self, movetime=None, depth=None, infinite: bool = False):
        self.searches.append(self._board.fen())

        legal = list(self._board.legal_moves)
        if not legal:
            self._pending = ["bestmove 0000"]
            return

        lines = []
        for rank in range(1, min(3, len(legal)) + 1):
            move = legal[rank - 1]
            lines.append(
                f"info depth 15 multipv {rank} score cp {30 - 10 * rank} pv {move.uci()}"
            )
        lines.append(f"bestmove {legal[0].uci()}")
        self._pending = lines

    def stop_analysis(self):
        pass

    def get_output(self):
        lines, self._pending = self._pending, []
        return lines


def board_with_pgn(pgn: str) -> GameState:
    state = GameState()
    assert state.load_pgn(pgn)
    return state


def run(game_state: GameState, **settings) -> tuple:
    engine = FakeEngine()
    analysis = AnalysisEngine(game_state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = engine
    analysis.time_per_move = settings.pop("time_per_move", 50)
    analysis.depth = settings.pop("depth", None)
    analysis.skip_analyzed = settings.pop("skip_analyzed", True)

    analysis.start_analysis()
    assert analysis._thread is not None
    analysis._thread.join(timeout=30)
    assert not analysis._thread.is_alive()

    return analysis, engine


def test_first_run_analyzes_every_move():
    state = board_with_pgn(PGN)

    analysis, engine = run(state)

    assert len(state.moves) == 6
    assert analysis.analyzed_move_count == 6
    assert analysis.skipped_move_count == 0
    assert len(engine.searches) == 12
    assert all(move.has_analysis() for move in state.moves)


def test_second_run_does_not_touch_the_engine():
    state = board_with_pgn(PGN)
    run(state)

    analysis, engine = run(state)

    assert analysis.analyzed_move_count == 0
    assert analysis.skipped_move_count == 6
    assert engine.searches == []
    assert engine.started is False


def test_kept_moves_survive_a_second_run_unchanged():
    state = board_with_pgn(PGN)
    run(state)
    before = [(m.move.uci(), m.classification, m.analysis_signature) for m in state.moves]

    run(state)

    after = [(m.move.uci(), m.classification, m.analysis_signature) for m in state.moves]
    assert before == after


def test_changing_a_tail_move_only_analyzes_the_tail():
    state = board_with_pgn(PGN)
    run(state)

    state.go_to_move(2)
    assert state.make_move(chess.Move.from_uci("g8f6")) is not None
    assert len(state.moves) == 4
    assert state.moves[3].move.uci() == "g8f6"
    assert not state.moves[3].has_analysis()

    analysis, engine = run(state)

    assert analysis.analyzed_move_count == 1
    assert analysis.skipped_move_count == 3
    assert len(engine.searches) == 2
    assert all(move.has_analysis() for move in state.moves)


def test_pending_count_reports_only_the_new_tail():
    state = board_with_pgn(PGN)
    run(state)

    state.go_to_move(2)
    state.make_move(chess.Move.from_uci("g8f6"))

    engine = FakeEngine()
    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = engine
    analysis.time_per_move = 50

    assert analysis.pending_move_count() == 1
    assert analysis.has_pending_moves is True


def test_pending_count_is_zero_after_a_full_run():
    state = board_with_pgn(PGN)
    run(state)

    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = FakeEngine()
    analysis.time_per_move = 50

    assert analysis.pending_move_count() == 0
    assert analysis.has_pending_moves is False


def test_changing_the_time_limit_invalidates_every_move():
    state = board_with_pgn(PGN)
    run(state, time_per_move=50)

    analysis, engine = run(state, time_per_move=200)

    assert analysis.analyzed_move_count == 6
    assert analysis.skipped_move_count == 0
    assert len(engine.searches) == 12


def test_changing_the_depth_invalidates_every_move():
    state = board_with_pgn(PGN)
    run(state, depth=None)

    analysis, _ = run(state, depth=12)

    assert analysis.analyzed_move_count == 6


def test_changing_the_multipv_count_invalidates_every_move():
    state = board_with_pgn(PGN)
    run(state)

    engine = FakeEngine()
    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = engine
    analysis.time_per_move = 50
    analysis.multipv = 1

    analysis.start_analysis()
    analysis._thread.join(timeout=30)

    assert analysis.analyzed_move_count == 6
    assert analysis.skipped_move_count == 0


def test_a_different_engine_invalidates_every_move():
    state = board_with_pgn(PGN)
    run(state)

    engine = FakeEngine(engine_path="another-engine")
    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = engine
    analysis.time_per_move = 50

    analysis.start_analysis()
    analysis._thread.join(timeout=30)

    assert analysis.analyzed_move_count == 6


def test_skipping_can_be_turned_off():
    state = board_with_pgn(PGN)
    run(state)

    analysis, engine = run(state, skip_analyzed=False)

    assert analysis.analyzed_move_count == 6
    assert analysis.skipped_move_count == 0
    assert len(engine.searches) == 12


def test_unknown_results_are_retried():
    state = board_with_pgn(PGN)
    run(state)

    signature = state.moves[0].analysis_signature
    state.moves[0].classification = "Unknown"
    state.moves[0].analysis_signature = None

    engine = FakeEngine()
    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = engine
    analysis.time_per_move = 50

    assert state.moves[0].is_analyzed_for(signature) is False
    assert analysis.pending_move_count() == 1


def test_branch_restore_reuses_cached_analysis():
    state = board_with_pgn(PGN)
    run(state)

    state.go_to_move(4)
    assert state.make_move(chess.Move.from_uci("g8f6")) is not None
    assert len(state.moves) == 6
    assert state.moves[5].move.uci() == "g8f6"

    analysis, _ = run(state)
    assert analysis.analyzed_move_count == 1
    assert analysis.skipped_move_count == 5

    state.go_to_move(4)
    assert len(state.branches) == 1
    state.activate_branch(state.branches[0])
    assert [m.move.uci() for m in state.moves] == [
        "e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6",
    ]

    analysis, engine = run(state)

    assert analysis.skipped_move_count == 6
    assert analysis.analyzed_move_count == 0
    assert engine.searches == []


def test_move_signature_reacts_to_the_position():
    state = board_with_pgn(PGN)
    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = FakeEngine()
    analysis.time_per_move = 50

    start = chess.Board()
    other = chess.Board()
    other.push(chess.Move.from_uci("e2e4"))

    move = chess.Move.from_uci("g1f3")
    assert analysis.move_signature(start, move) != analysis.move_signature(other, move)

    pawn_push = chess.Move.from_uci("e2e4")
    assert analysis.move_signature(start, move) != analysis.move_signature(start, pawn_push)


def test_settings_signature_covers_the_engine_and_limits():
    state = board_with_pgn(PGN)
    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = FakeEngine()
    analysis.time_per_move = 50
    baseline = analysis.settings_signature()

    analysis.time_per_move = 100
    assert analysis.settings_signature() != baseline

    analysis.time_per_move = 50
    analysis.depth = 9
    assert analysis.settings_signature() != baseline

    analysis.depth = None
    analysis.multipv = 2
    assert analysis.settings_signature() != baseline

    analysis.multipv = 3
    assert analysis.settings_signature() == baseline

    analysis.engine = FakeEngine(engine_path="other")
    assert analysis.settings_signature() != baseline


def test_a_move_without_a_signature_is_not_considered_analyzed():
    state = board_with_pgn(PGN)
    for move in state.moves:
        move.classification = "Best"
        move.analysis_signature = None

    analysis = AnalysisEngine(state, "fake", EngineProtocol.UCI, MoveClassifier())
    analysis.engine = FakeEngine()
    analysis.time_per_move = 50

    assert analysis.pending_move_count() == 6
