from __future__ import annotations
import time
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import chess

from .engine_manager import EngineManager, EngineProtocol
from .models.game_state import MoveEval


class QuickEvaluator(QObject):
    eval_ready = pyqtSignal(object, object, object)
    engine_output = pyqtSignal(str)

    def __init__(self, engine_path: str = "",
                 protocol: EngineProtocol = EngineProtocol.UCI,
                 movetime_ms: int = 7000):
        super().__init__()
        self._engine_path = engine_path
        self._protocol = protocol
        self._movetime_ms = movetime_ms

        self._engine: Optional[EngineManager] = None
        self._running = False
        self._timer: Optional[QTimer] = None
        self._start_time = 0.0
        self._board_turn = chess.WHITE
        self._fen: Optional[str] = None

        self._generation = 0
        self._running_generation = 0

        self._last_pv: Optional[chess.Move] = None
        self._last_score_cp: Optional[float] = None
        self._last_mate: Optional[int] = None
        self._last_depth: int = 0
        self._awaiting_stop = False
        self._pending_fen: Optional[str] = None
        self._pending_gen = 0
        self._pending_board: Optional[chess.Board] = None
        self._infinite = False

    def ensure_started(self) -> bool:
        if self._engine is not None and self._engine._ready:
            return True
        self._engine = EngineManager(self._engine_path, self._protocol)
        return self._engine.start()

    def _launch_search(self, board: chess.Board, gen: int, infinite: bool = False):
        if not self.ensure_started():
            return
        self._engine.set_position(board)
        self._engine.get_output()
        if infinite:
            self._engine.start_analysis(infinite=True)
        else:
            self._engine.start_analysis(movetime=self._movetime_ms)
        self._board_turn = board.turn
        self._fen = board.fen()
        self._running_generation = gen
        self._running = True
        self._awaiting_stop = False
        self._infinite = infinite
        self._start_time = time.time()

    def evaluate(self, board: chess.Board):
        if not self.ensure_started():
            return

        self._generation += 1
        current_gen = self._generation

        board_changed = (self._fen is not None and self._fen != board.fen())
        if board_changed:
            self._last_pv = None
            self._last_score_cp = None
            self._last_mate = None
            self._last_depth = 0

        if self._running:
            if not self._awaiting_stop and not self._infinite:
                self._awaiting_stop = True
                self._engine.stop_analysis()
                self._engine.get_output()
            if self._infinite:
                self._engine.stop_analysis()
                self._engine.get_output()
                self._launch_search(board, current_gen, infinite=True)
            else:
                self._pending_board = board
                self._pending_fen = board.fen()
                self._pending_gen = current_gen
                if self._timer is None:
                    self._timer = QTimer()
                    self._timer.timeout.connect(self._poll)
                    self._timer.start(50)
            return

        if self._timer:
            self._timer.stop()

        self._launch_search(board, current_gen)

        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._poll)
        self._timer.start(50)

    def evaluate_infinite(self, board: chess.Board):
        """Start infinite (live) analysis. Runs until stop() is called."""
        if not self.ensure_started():
            return

        self._generation += 1
        current_gen = self._generation

        if self._running:
            self._engine.stop_analysis()
            self._engine.get_output()

        self._launch_search(board, current_gen, infinite=True)

        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._poll)
        self._timer.start(50)

    def _poll(self):
        if self._engine is None:
            self._stop()
            return

        lines = self._engine.get_output()

        if self._awaiting_stop:
            bestmove_found = False
            for line in lines:
                if line.startswith("bestmove"):
                    bestmove_found = True
                    break
            if bestmove_found and self._pending_board is not None:
                self._launch_search(self._pending_board, self._pending_gen)
                self._pending_board = None
                self._pending_fen = None
                self._pending_gen = 0
            elif bestmove_found:
                self._stop()
                return
            else:
                return

        if not self._running or self._engine is None:
            self._stop()
            return

        my_gen = self._running_generation
        if my_gen != self._generation:
            self._stop()
            return

        timeout = not self._infinite and (time.time() - self._start_time > self._movetime_ms / 1000.0 + 0.5)

        for line in lines:
            self.engine_output.emit(line)
            if self._generation != my_gen:
                self._stop()
                return

            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        bm = chess.Move.from_uci(parts[1])
                        self._last_pv = bm
                    except:
                        pass
                self._emit_final()
                if self._infinite:
                    if self._engine and self._fen is not None:
                        try:
                            board = chess.Board(self._fen)
                            self._engine.stop_analysis()
                            self._engine.get_output()
                            self._launch_search(board, self._generation, infinite=True)
                        except:
                            self._stop()
                    return
                else:
                    self._stop()
                    return

            info = self._engine.parse_uci_info(line)
            if info is None:
                continue

            score_cp = info.get('score_cp')
            mate = info.get('mate')
            depth = info.get('depth', 0)

            if score_cp is not None or mate is not None:
                if score_cp is not None:
                    self._last_score_cp = float(score_cp)
                self._last_mate = mate
                self._last_depth = depth

                if 'pv' in info:
                    try:
                        pv_strs = info['pv'].split()
                        if pv_strs:
                            self._last_pv = chess.Move.from_uci(pv_strs[0])
                    except:
                        pass

                pv_to_emit = self._last_pv
                ev = MoveEval(
                    move=pv_to_emit or chess.Move.null(),
                    score_cp=float(score_cp) if score_cp is not None else None,
                    mate=mate,
                    depth=depth
                )

                turn = self._board_turn
                self.eval_ready.emit(ev, pv_to_emit, turn)

        if timeout:
            self._emit_final()
            self._stop()

    def _emit_final(self):
        if self._last_score_cp is not None or self._last_mate is not None:
            pv_to_emit = self._last_pv
            ev = MoveEval(
                move=pv_to_emit or chess.Move.null(),
                score_cp=self._last_score_cp,
                mate=self._last_mate,
                depth=self._last_depth
            )
            turn = self._board_turn
            self.eval_ready.emit(ev, pv_to_emit, turn)

    def _finish(self):
        self._running = False
        self._awaiting_stop = False
        self._fen = None
        self._pending_board = None
        self._pending_fen = None
        self._pending_gen = 0
        if self._timer:
            self._timer.stop()
        try:
            if self._engine:
                self._engine.stop_analysis()
                self._engine.get_output()
        except:
            pass

    def _stop(self):
        self._running = False
        self._awaiting_stop = False
        self._infinite = False
        self._fen = None
        self._pending_board = None
        self._pending_fen = None
        self._pending_gen = 0
        if self._timer:
            self._timer.stop()
        try:
            if self._engine:
                self._engine.stop_analysis()
                self._engine.get_output()
        except:
            pass

    def stop(self):
        self._stop()
        if self._engine:
            self._engine.stop()
            self._engine = None

    def is_stale(self, board: chess.Board) -> bool:
        return self._fen is not None and self._fen != board.fen()

    def update_settings(self, engine_path: str, protocol: EngineProtocol, movetime_ms: int):
        needs_restart = (engine_path != self._engine_path or protocol != self._protocol)
        self._engine_path = engine_path
        self._protocol = protocol
        self._movetime_ms = movetime_ms
        if needs_restart:
            self.stop()

    def stop_analysis_only(self):
        self._running = False
        self._awaiting_stop = False
        self._infinite = False
        self._pending_board = None
        self._pending_fen = None
        self._pending_gen = 0
        if self._timer:
            self._timer.stop()
        if self._engine:
            try:
                self._engine.stop_analysis()
                self._engine.get_output()
            except:
                pass
        self._fen = None
