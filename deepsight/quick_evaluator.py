from __future__ import annotations
import time
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import chess

from .engine_manager import EngineManager, EngineProtocol
from .models.game_state import MoveEval

class QuickEvaluator(QObject):

    eval_ready = pyqtSignal(object, object, object)

    def __init__(self, engine_path: str = "Engines/Ember.exe",
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

    def ensure_started(self) -> bool:
        if self._engine is not None and self._engine._ready:
            return True
        self._engine = EngineManager(self._engine_path, self._protocol)
        return self._engine.start()

    def evaluate(self, board: chess.Board):

        if not self.ensure_started():
            return

        self._board_turn = board.turn
        self._fen = board.fen()

        try:
            self._engine.stop_analysis()
        except:
            pass

        self._engine.set_position(board)
        self._engine.get_output()
        self._engine.start_analysis(movetime=self._movetime_ms)

        self._running = True
        self._start_time = time.time()

        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._poll)
        self._timer.start(50)

    def _poll(self):
        if not self._running or self._engine is None:
            self._stop()
            return

        lines = self._engine.get_output()
        timeout = time.time() - self._start_time > self._movetime_ms / 1000.0 + 0.5

        for line in lines:
            if line.startswith("bestmove"):
                self._finish()
                return

            info = self._engine.parse_uci_info(line)
            if info is None:
                continue

            score_cp = info.get('score_cp')
            mate = info.get('mate')
            depth = info.get('depth', 0)

            if score_cp is not None or mate is not None:
                pv = None
                if 'pv' in info:
                    try:
                        pv_strs = info['pv'].split()
                        if pv_strs:
                            pv = chess.Move.from_uci(pv_strs[0])
                    except:
                        pass

                ev = MoveEval(
                    move=pv or chess.Move.null(),
                    score_cp=float(score_cp) if score_cp is not None else None,
                    mate=mate,
                    depth=depth
                )
                self.eval_ready.emit(ev, pv, self._board_turn)

        if timeout:
            self._finish()

    def _finish(self):
        self._running = False
        self._fen = None
        if self._timer:
            self._timer.stop()
        try:
            self._engine.stop_analysis()
        except:
            pass

    def _stop(self):
        self._running = False
        self._fen = None
        if self._timer:
            self._timer.stop()
        try:
            if self._engine:
                self._engine.stop_analysis()
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
        if self._timer:
            self._timer.stop()
        if self._engine:
            try:
                self._engine.stop_analysis()
                self._engine.get_output()
            except:
                pass
        self._fen = None