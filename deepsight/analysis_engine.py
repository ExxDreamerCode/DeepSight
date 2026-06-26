from __future__ import annotations
import threading
import time
from typing import Optional, Callable, List, Dict, Any
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

import chess

from .engine_manager import EngineManager, EngineProtocol
from .models.game_state import GameState, MoveEval, AnalyzedMove
from .move_classifier import MoveClassifier

class AnalysisMode(Enum):
    FIXED = "fixed"
    LIVE = "live"

class AnalysisEngine(QObject):

    progress_changed = pyqtSignal(int, int)
    move_analyzed = pyqtSignal(object)
    live_updated = pyqtSignal(object, object, object)
    analysis_complete = pyqtSignal()
    analysis_error = pyqtSignal(str)

    def __init__(self, game_state: GameState, engine_path: str,
                 protocol: EngineProtocol = EngineProtocol.UCI,
                 classifier: Optional[MoveClassifier] = None,
                 use_nnue: bool = False):
        super().__init__()
        self.game_state = game_state
        self.engine = EngineManager(engine_path, protocol)
        self.engine._use_nnue = use_nnue
        self.classifier = classifier or MoveClassifier()

        self.time_per_move: int = 1000
        self.depth: Optional[int] = None
        self._use_nnue = use_nnue

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._live_eval: Optional[MoveEval] = None
        self._live_best_move: Optional[chess.Move] = None

    def start_analysis(self):

        if self._running:
            return

        if not self.game_state.moves:
            self.analysis_error.emit("No moves to analyze. Load a PGN or make moves on the board first.")
            return

        self._running = True
        self._stop_event.clear()

        if not self.engine.start():
            self._running = False
            self.analysis_error.emit("Failed to start engine")
            return

        self._thread = threading.Thread(target=self._analyze_all, daemon=True)
        self._thread.start()

    def start_live_analysis(self):

        if self._running:
            self._restart_live()
            return

        self._running = True
        self._stop_event.clear()

        if not self.engine.start():
            self._running = False
            self.analysis_error.emit("Failed to start engine")
            return

        self._thread = threading.Thread(target=self._live_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        try:
            self.engine.stop_analysis()
        except:
            pass
        time.sleep(0.1)
        self.engine.stop()

    def pause(self):
        if self._running:
            self._paused = True
            try:
                self.engine.stop_analysis()
            except:
                pass

    def resume(self):
        if self._running:
            self._paused = False
            self.engine.start_analysis(infinite=True)

    def send_move(self, move: chess.Move):

        self.game_state.board.push(move)

        player = not self.game_state.board.turn
        try:
            san = self.game_state.board.san(move)
        except:
            san = move.uci()

        analyzed = AnalyzedMove(
            move_number=len(self.game_state.moves) + 1,
            move=move,
            san=san,
            player=player
        )
        self.game_state.moves.append(analyzed)
        self.game_state.current_move_index = len(self.game_state.moves) - 1

        if self._running:
            self._restart_live()

    def _restart_live(self):
        try:
            self.engine.stop_analysis()
        except:
            pass
        time.sleep(0.05)
        self.engine.set_position(self.game_state.board)
        self.engine.start_analysis(infinite=True)

    def _parse_uci_line(self, line: str) -> tuple:

        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) > 1:
                try:
                    move = chess.Move.from_uci(parts[1])
                    return (None, move, True)
                except:
                    pass
            return (None, None, True)

        info = self.engine.parse_uci_info(line)
        if info is None:
            return (None, None, False)

        if 'pv' not in info and 'score_cp' not in info and 'mate' not in info:
            return (None, None, False)

        best_move = None
        pv_moves = []
        if 'pv' in info:
            try:
                for m_str in info['pv'].split():
                    pv_moves.append(chess.Move.from_uci(m_str))
                if pv_moves:
                    best_move = pv_moves[0]
            except:
                pass

        score_cp = info.get('score_cp')
        mate = info.get('mate')
        depth = info.get('depth', 0)

        if not best_move and score_cp is None and mate is None:
            return (None, None, False)

        eval_data = MoveEval(
            move=best_move or chess.Move.null(),
            score_cp=float(score_cp) if score_cp is not None else None,
            mate=mate,
            depth=depth,
            best_line=pv_moves
        )

        return (eval_data, best_move, False)

    def _analyze_all(self):

        total = len(self.game_state.moves)
        original_board = self.game_state.board.copy()

        try:
            for idx, move_data in enumerate(self.game_state.moves):
                if self._stop_event.is_set():
                    break

                self.engine.get_output()

                board_before = self.game_state.get_position_at(idx - 1)
                self.engine.set_position(board_before)

                self.engine.start_analysis(
                    movetime=self.time_per_move if not self.depth else None,
                    depth=self.depth
                )

                last_eval: Optional[MoveEval] = None
                best_move: Optional[chess.Move] = None
                start_time = time.time()
                timeout = (self.time_per_move if not self.depth else 10000) / 1000.0 + 1.0

                while not self._stop_event.is_set():
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        break

                    got_bestmove = False
                    lines = self.engine.get_output()
                    for line in lines:
                        eval_data, bm, is_bestmove = self._parse_uci_line(line)

                        if is_bestmove:
                            if bm:
                                best_move = bm
                            got_bestmove = True
                            break

                        if eval_data:
                            last_eval = eval_data
                            if bm:
                                best_move = bm

                            self.live_updated.emit(eval_data, best_move, move_data.player)

                    if got_bestmove or self._stop_event.is_set():
                        break

                    time.sleep(0.005)

                self.engine.stop_analysis()
                time.sleep(0.02)

                if not last_eval and best_move:
                    last_eval = MoveEval(move=best_move)

                eval_before_num = last_eval.score_num if last_eval else None
                final_depth = last_eval.depth if last_eval else 0

                classification = self.classifier.classify(
                    board_before=board_before,
                    played_move=move_data.move,
                    best_move=best_move,
                    eval_before=eval_before_num,
                    depth=final_depth
                )

                move_data.eval_before = last_eval
                move_data.best_move = best_move
                move_data.depth = final_depth
                move_data.classification = classification

                board_after = board_before.copy()
                board_after.push(move_data.move)
                self.engine.set_position(board_after)
                self.engine.get_output()
                self.engine.start_analysis(movetime=1500)

                after_eval = None
                after_start = time.time()
                after_timeout = 2.0
                while not self._stop_event.is_set():
                    if time.time() - after_start > after_timeout:
                        break
                    got_bestmove = False
                    lines = self.engine.get_output()
                    for line in lines:
                        if line.startswith("bestmove"):
                            got_bestmove = True
                            break
                        info = self.engine.parse_uci_info(line)
                        if info:
                            score_cp = info.get('score_cp')
                            mate = info.get('mate')
                            depth = info.get('depth', 0)
                            if score_cp is not None or mate is not None:
                                after_eval = MoveEval(
                                    move=chess.Move.null(),
                                    score_cp=float(score_cp) if score_cp is not None else None,
                                    mate=mate,
                                    depth=depth
                                )
                    if got_bestmove:
                        break
                    time.sleep(0.01)

                self.engine.stop_analysis()
                time.sleep(0.02)

                if after_eval:
                    move_data.eval_after = after_eval
                    eval_after_num = after_eval.score_num

                    new_class = self.classifier.classify(
                        board_before=board_before,
                        played_move=move_data.move,
                        best_move=best_move,
                        eval_before=eval_before_num,
                        eval_after=eval_after_num,
                        depth=final_depth
                    )
                    if new_class != move_data.classification:
                        move_data.classification = new_class
                        self.move_analyzed.emit(move_data)
                else:
                    eval_after_num = None

                self.move_analyzed.emit(move_data)

                if idx > 0 and last_eval and last_eval.score_num is not None:
                    prev_move = self.game_state.moves[idx - 1]
                    prev_before = prev_move.eval_before.score_num if prev_move.eval_before else None
                    if prev_before is not None:
                        prev_eval_after = last_eval.score_num
                        prev_depth = prev_move.depth or (after_eval.depth if after_eval else final_depth)
                        new_class = self.classifier.classify(
                            board_before=self.game_state.get_position_at(idx - 2),
                            played_move=prev_move.move,
                            best_move=prev_move.best_move,
                            eval_before=prev_before,
                            eval_after=prev_eval_after,
                            depth=prev_depth
                        )
                        if new_class != prev_move.classification:
                            prev_move.classification = new_class
                            self.move_analyzed.emit(prev_move)

                self.progress_changed.emit(idx + 1, total)

            self.game_state.board = original_board

            if not self._stop_event.is_set():
                self.analysis_complete.emit()

        except Exception as e:
            import traceback
            self.analysis_error.emit(f"Analysis error: {e}\n{traceback.format_exc()}")

        finally:
            self._running = False
            self.engine.stop()

    def _live_loop(self):

        try:
            self.engine.set_position(self.game_state.board)
            self.engine.start_analysis(infinite=True)

            while self._running and not self._stop_event.is_set():
                if self._paused:
                    time.sleep(0.1)
                    continue

                lines = self.engine.get_output()
                for line in lines:
                    eval_data, best_move, is_bestmove = self._parse_uci_line(line)
                    if eval_data:
                        self._live_eval = eval_data
                        self._live_best_move = best_move
                        self.live_updated.emit(eval_data, best_move, self.game_state.board.turn)

                time.sleep(0.05)

        except Exception as e:
            self.analysis_error.emit(f"Live analysis error: {e}")

        finally:
            self.engine.stop()

    @property
    def live_eval(self) -> Optional[MoveEval]:
        return self._live_eval

    @property
    def live_best_move(self) -> Optional[chess.Move]:
        return self._live_best_move
