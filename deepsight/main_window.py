from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout,
                             QStatusBar, QLabel, QProgressBar,
                             QMessageBox, QMenuBar, QMenu, QFileDialog,
                             QDialog, QVBoxLayout, QTextEdit, QPushButton)
from PyQt6.QtCore import Qt, QTimer, QMutex, QMutexLocker
from PyQt6.QtGui import QAction

import chess

from .models.game_state import GameState, MoveEval, AnalyzedMove
from .board_widget import BoardWidget
from .eval_bar import EvalBar
from .move_list_panel import MoveListPanel
from .input_panel import InputPanel
from .analysis_engine import AnalysisEngine
from .engine_manager import EngineProtocol
from .move_classifier import MoveClassifier, BookChecker
from .quick_evaluator import QuickEvaluator


class EngineOutputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Engine Output")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("background: #1a1a1a; color: #0f0; font-family: monospace;")
        layout.addWidget(self.text)
        btn = QPushButton("Clear")
        btn.clicked.connect(self.text.clear)
        layout.addWidget(btn)

    def append(self, text: str):
        self.text.append(text)
        sb = self.text.verticalScrollBar()
        sb.setValue(sb.maximum())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DeepSight - Chess Analyzer")
        self.setMinimumSize(1100, 700)

        self.game_state = GameState()
        self.book_checker = BookChecker("Books")
        self.classifier = MoveClassifier(self.book_checker)
        book_count = self.book_checker.load_books()
        print(f"Loaded {book_count} book moves")

        self.analysis: Optional[AnalysisEngine] = None
        self._skip_live = False
        self._debug_dialog = EngineOutputDialog(self)
        self.quick_eval: Optional[QuickEvaluator] = None
        self._last_live_eval: Optional[MoveEval] = None
        self._last_live_best_move: Optional[chess.Move] = None
        self._last_live_fen: Optional[str] = None
        self._eval_mutex = QMutex()
        self._quick_eval_pending = False
        self._quick_eval_timer: Optional[QTimer] = None

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

        QTimer.singleShot(500, self._quick_evaluate)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.book_indicator = QLabel("")
        self.book_indicator.setStyleSheet("color: #888; font-style: italic;")
        self.status_bar.addPermanentWidget(self.book_indicator)

        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; }
            QStatusBar { background: #222; color: #aaa; }
            QMenuBar { background: #222; color: #ccc; }
            QMenuBar::item:selected { background: #444; }
            QMenu { background: #2a2a2a; color: #ccc; border: 1px solid #555; }
            QMenu::item:selected { background: #4a4a4a; }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self.input_panel = InputPanel(self.game_state)
        self.input_panel.setFixedWidth(300)
        main_layout.addWidget(self.input_panel)

        center = QWidget()
        cl = QHBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)

        self.board = BoardWidget(self.game_state)
        cl.addWidget(self.board, 1)

        self.eval_bar = EvalBar()
        cl.addWidget(self.eval_bar)

        main_layout.addWidget(center, 1)

        self.move_list = MoveListPanel(self.game_state)
        self.move_list.setMinimumWidth(280)
        main_layout.addWidget(self.move_list)

    def _setup_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        a = QAction("Load PGN...", self)
        a.triggered.connect(self._menu_load_pgn)
        fm.addAction(a)
        fm.addSeparator()
        a = QAction("Exit", self)
        a.triggered.connect(self.close)
        fm.addAction(a)

        vm = mb.addMenu("View")
        a = QAction("Flip Board", self)
        a.triggered.connect(self.board.flip_board)
        vm.addAction(a)

        dm = mb.addMenu("Debug")
        a = QAction("Show Engine Output", self)
        a.triggered.connect(self._debug_dialog.show)
        dm.addAction(a)
        a = QAction("Test Engine Direct", self)
        a.triggered.connect(self._test_engine_direct)
        dm.addAction(a)

        am = mb.addMenu("Analysis")
        a = QAction("Start Analysis", self)
        a.triggered.connect(lambda: self._start_analysis("start"))
        am.addAction(a)
        a = QAction("Stop", self)
        a.triggered.connect(self._stop_analysis)
        am.addAction(a)

    def _connect_signals(self):
        self.input_panel.pgn_loaded.connect(self._on_pgn_loaded)
        self.input_panel.fen_loaded.connect(self._on_fen_loaded)
        self.input_panel.analysis_started.connect(self._start_analysis)
        self.input_panel.analysis_stopped.connect(self._stop_analysis)
        self.input_panel.move_input.connect(self._on_manual_move)
        self.input_panel.clear_requested.connect(self._on_clear)
        self.board.move_made.connect(self._on_board_move)
        self.move_list.move_selected.connect(self._on_move_selected)
        self.input_panel.analysis_stopped.connect(self._stop_quick_eval)

    def _debug(self, text: str):
        self._debug_dialog.append(text)
        print(text)

    def _test_engine_direct(self):
        ep = self.input_panel.get_engine_path()
        pr = self.input_panel.get_protocol()
        self._debug(f"Testing engine: {ep} ({pr.value})")
        from .engine_manager import EngineManager
        eng = EngineManager(ep, pr)
        ok = eng.start()
        self._debug(f"Engine start: {ok}")
        if not ok:
            return
        eng.set_position_from_moves([])
        eng.start_analysis(movetime=2000)
        import time
        time.sleep(2.5)
        eng.stop_analysis()
        eng.stop()
        lines = eng.get_output()
        self._debug(f"Engine output ({len(lines)} lines):")
        for l in lines:
            self._debug(f"  {l}")

    def _on_pgn_loaded(self, text: str):
        self._stop_analysis()
        self._stop_quick_eval()
        if self.game_state.load_pgn(text):
            self.board.update()
            self.eval_bar.clear()
            self.move_list.refresh()
            self.status_label.setText(f"Loaded PGN: {len(self.game_state.moves)} moves")
            self._quick_evaluate()
        else:
            QMessageBox.warning(self, "Error", "Failed to parse PGN")

    def _on_fen_loaded(self, fen: str):
        self._stop_analysis()
        self._stop_quick_eval()
        if self.game_state.load_fen(fen):
            self.board.update()
            self.eval_bar.clear()
            self.move_list.refresh()
            self.status_label.setText("Loaded FEN position")
            self._quick_evaluate()
        else:
            QMessageBox.warning(self, "Error", "Invalid FEN")

    def _make_move(self, move: chess.Move):
        if not self.game_state.board.is_legal(move):
            return

        with QMutexLocker(self._eval_mutex):
            self._quick_eval_pending = False
            if self._quick_eval_timer:
                self._quick_eval_timer.stop()
                self._quick_eval_timer = None

        self._stop_quick_eval()

        if self.game_state.current_move_index < len(self.game_state.moves) - 1:
            del self.game_state.moves[self.game_state.current_move_index + 1:]
            self.game_state.board = chess.Board()
            for m in self.game_state.moves:
                self.game_state.board.push(m.move)

        player = self.game_state.board.turn
        try:
            san = self.game_state.board.san(move)
        except:
            san = move.uci()

        am = AnalyzedMove(
            move_number=len(self.game_state.moves) + 1,
            move=move, san=san, player=player
        )

        self.game_state.moves.append(am)
        self.game_state.board.push(move)
        self.game_state.current_move_index = len(self.game_state.moves) - 1

        self.board.update()
        self.move_list.refresh()
        self.eval_bar.clear()
        self.board.clear_arrow()
        self._skip_live = True

        self.status_label.setText(f"Move {len(self.game_state.moves)}: {am.san}")

        self._quick_evaluate()

    def _on_manual_move(self, s: str):
        try:
            m = chess.Move.from_uci(s)
            if m in self.game_state.board.legal_moves:
                self._make_move(m)
                return
        except:
            pass
        try:
            m = self.game_state.board.parse_san(s)
            if m in self.game_state.board.legal_moves:
                self._make_move(m)
                return
        except:
            pass
        QMessageBox.warning(self, "Error", f"Invalid move: {s}")

    def _on_board_move(self, m: chess.Move):
        self._make_move(m)

    def _on_clear(self):
        self._stop_analysis()
        self._stop_quick_eval()
        self.game_state.clear()
        self.board.update()
        self.eval_bar.clear()
        self.move_list.refresh()
        self.board.clear_arrow()
        self.board.set_last_move(None)
        self.book_indicator.setText("")
        self.status_label.setText("Ready")

    def _on_move_selected(self, idx: int):
        self.game_state.go_to_move(idx)
        self.board.update()
        cur = self.game_state.current_move

        if cur:
            self.board.set_last_move(cur.move)

            if cur.best_move:
                self.board.set_best_move_arrow(cur.best_move.from_square, cur.best_move.to_square)
            else:
                self.board.clear_arrow()

            ev_after = cur.eval_after
            ev_before_next = None
            if idx + 1 < len(self.game_state.moves):
                ev_before_next = self.game_state.moves[idx + 1].eval_before

            if ev_after:
                board_after = self.game_state.get_position_at(idx)
                turn_after = board_after.turn
                score_cp = ev_after.score_cp
                if score_cp is not None and turn_after == chess.BLACK:
                    score_cp = -score_cp
                self.eval_bar.set_eval(score_cp=score_cp, mate=ev_after.mate, depth=ev_after.depth or 0)
            elif ev_before_next:
                next_move = self.game_state.moves[idx + 1]
                score_cp = ev_before_next.score_cp
                if score_cp is not None and next_move.player == chess.BLACK:
                    score_cp = -score_cp
                self.eval_bar.set_eval(score_cp=score_cp, mate=ev_before_next.mate, depth=ev_before_next.depth or 0)
            elif cur.eval_before:
                ev = cur.eval_before
                score_cp = ev.score_cp
                if score_cp is not None and cur.player == chess.BLACK:
                    score_cp = -score_cp
                self.eval_bar.set_eval(score_cp=score_cp, mate=ev.mate, depth=ev.depth or 0)
            else:
                self.eval_bar.clear()

            if cur.eval_before or cur.eval_after:
                if cur.classification:
                    self.status_label.setText(f"Move {cur.move_number}: {cur.san} — {cur.classification}")
                else:
                    self.status_label.setText(f"Move {cur.move_number}: {cur.san}")
            else:
                self.status_label.setText(f"Move {cur.move_number}: {cur.san}")
                self._quick_evaluate()
        else:
            self.board.clear_arrow()
            self.board.set_last_move(None)
            self.eval_bar.clear()

    def _start_analysis(self, _):
        self._stop_analysis()
        self._skip_live = False

        with QMutexLocker(self._eval_mutex):
            self._quick_eval_pending = False
            if self._quick_eval_timer:
                self._quick_eval_timer.stop()
                self._quick_eval_timer = None

        ep = self.input_panel.get_engine_path()
        pr = self.input_panel.get_protocol()
        if not self.game_state.moves:
            QMessageBox.warning(self, "Warning", "No moves to analyze. Load PGN or make moves first.")
            return

        self._debug(f"Starting analysis: engine={ep}, protocol={pr.value}, moves={len(self.game_state.moves)}")

        self._stop_quick_eval()

        self.analysis = AnalysisEngine(self.game_state, ep, pr, self.classifier,
                                       use_nnue=self.input_panel.get_nnue())
        self.analysis.time_per_move = self.input_panel.get_time_per_move()
        self.analysis.depth = self.input_panel.get_depth()

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.game_state.moves))
        self.progress_bar.setValue(0)

        self.analysis.live_updated.connect(self._on_live_update)
        self.analysis.move_analyzed.connect(self._on_move_analyzed)
        self.analysis.progress_changed.connect(self._on_analysis_progress)
        self.analysis.analysis_complete.connect(self._on_analysis_complete)
        self.analysis.analysis_error.connect(self._on_analysis_error)

        self.status_label.setText("Analyzing...")
        self.analysis.start_analysis()

    def _stop_analysis(self):
        if self.analysis:
            try:
                self.analysis.stop()
            except:
                pass
            for s in ('move_analyzed', 'progress_changed', 'analysis_complete', 'live_updated', 'analysis_error'):
                try:
                    getattr(self.analysis, s).disconnect()
                except:
                    pass
            self.analysis = None
        self.progress_bar.setVisible(False)
        self.input_panel.on_analysis_complete()
        self.status_label.setText("Analysis stopped")

    def _quick_evaluate(self):
        with QMutexLocker(self._eval_mutex):
            if self._quick_eval_pending:
                return
            self._quick_eval_pending = True

        if self.analysis is not None:
            with QMutexLocker(self._eval_mutex):
                self._quick_eval_pending = False
            return

        if self._quick_eval_timer is None:
            self._quick_eval_timer = QTimer()
            self._quick_eval_timer.setSingleShot(True)
            self._quick_eval_timer.timeout.connect(self._do_quick_evaluate)
        else:
            self._quick_eval_timer.stop()

        self._quick_eval_timer.start(100)

    def _do_quick_evaluate(self):
        with QMutexLocker(self._eval_mutex):
            self._quick_eval_pending = False
            self._quick_eval_timer = None

        if self.analysis is not None:
            return

        ep = self.input_panel.get_engine_path()
        pr = self.input_panel.get_protocol()

        if self.quick_eval is None:
            self.quick_eval = QuickEvaluator(ep, pr, movetime_ms=1500)
            self.quick_eval.eval_ready.connect(self._on_quick_eval)
        else:
            self.quick_eval.update_settings(ep, pr, movetime_ms=1500)

        self.quick_eval.evaluate(self.game_state.board)

    def _on_quick_eval(self, ev, bm, side):
        with QMutexLocker(self._eval_mutex):
            if self.analysis is not None:
                return

        if self.quick_eval and self.quick_eval.is_stale(self.game_state.board):
            return

        self._last_live_eval = ev
        self._last_live_best_move = bm
        self._last_live_fen = self.game_state.board.fen()

        score_cp = ev.score_cp
        if score_cp is not None and side == chess.BLACK:
            score_cp = -score_cp

        self.eval_bar.set_eval(score_cp=score_cp, mate=ev.mate, depth=ev.depth or 0)
        if bm:
            self.board.set_best_move_arrow(bm.from_square, bm.to_square)

        if score_cp is not None:
            display = f"{score_cp / 100.0:+.2f}"
        elif ev.mate is not None:
            display = f"#{ev.mate}"
        else:
            display = "?"
        self.status_label.setText(f"Move {len(self.game_state.moves)}: {display} (depth={ev.depth})")

    def _stop_quick_eval(self):
        with QMutexLocker(self._eval_mutex):
            self._quick_eval_pending = False
            if self._quick_eval_timer:
                self._quick_eval_timer.stop()
                self._quick_eval_timer = None

        if self.quick_eval:
            try:
                self.quick_eval.stop()
            except:
                pass
            self.quick_eval = None

    def _on_analysis_progress(self, cur: int, total: int):
        self.progress_bar.setValue(cur)
        self.status_label.setText(f"Analyzing move {cur}/{total}")

    def _on_move_analyzed(self, md):
        self.move_list.refresh()
        try:
            idx = self.game_state.moves.index(md)
        except ValueError:
            return
        self.move_list._select_move(idx)
        self.move_list.scroll_to_move(idx)

    def _on_analysis_complete(self):
        self.progress_bar.setVisible(False)
        self.input_panel.on_analysis_complete()
        last_idx = self.game_state.current_move_index
        self.analysis = None
        if self.game_state.moves:
            if last_idx >= 0 and last_idx < len(self.game_state.moves):
                self._on_move_selected(last_idx)
            else:
                self._on_move_selected(0)
        self.status_label.setText("Analysis complete")
        self._debug("Analysis completed successfully")
        self._quick_evaluate()

    def _on_analysis_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.input_panel.on_analysis_complete()
        self.status_label.setText(f"Error: {msg}")
        self._debug(f"ANALYSIS ERROR: {msg}")
        QMessageBox.warning(self, "Analysis Error", msg)

    def _on_live_update(self, ev: MoveEval, bm: Optional[chess.Move], side: chess.Color):
        if self._skip_live:
            self._skip_live = False
            return

        score_cp = ev.score_cp
        if score_cp is not None and side == chess.BLACK:
            score_cp = -score_cp

        self.eval_bar.set_eval(score_cp=score_cp, mate=ev.mate, depth=ev.depth or 0)
        if bm:
            self.board.set_best_move_arrow(bm.from_square, bm.to_square)

        if score_cp is not None:
            display = f"{score_cp / 100.0:+.2f}"
        elif ev.mate is not None:
            display = f"#{ev.mate}"
        else:
            display = "?"
        self.status_label.setText(f"Analysis: {display} (depth={ev.depth})")

    def _menu_load_pgn(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Load PGN", "", "PGN Files (*.pgn);;All Files (*.*)")
        if fp:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    self._on_pgn_loaded(f.read())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load PGN: {e}")

    def closeEvent(self, event):
        self._stop_analysis()
        self._stop_quick_eval()
        event.accept()