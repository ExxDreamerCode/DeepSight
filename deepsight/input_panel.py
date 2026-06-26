from __future__ import annotations
from typing import Optional, Callable
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QComboBox, QFileDialog,
                             QLineEdit, QGroupBox, QFormLayout, QSpinBox,
                             QMessageBox, QRadioButton, QButtonGroup, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import chess

from .engine_manager import EngineProtocol
from .models.game_state import GameState

class InputPanel(QWidget):

    pgn_loaded = pyqtSignal(str)
    fen_loaded = pyqtSignal(str)
    analysis_started = pyqtSignal(str)
    analysis_stopped = pyqtSignal()
    move_input = pyqtSignal(str)
    clear_requested = pyqtSignal()

    def __init__(self, game_state: GameState, parent=None):
        super().__init__(parent)
        self.game_state = game_state
        self.engine_path: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("DeepSight")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4a9eff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        engine_group = QGroupBox("Engine")
        engine_layout = QVBoxLayout(engine_group)

        self.engine_path_label = QLabel("Ember (default)")
        self.engine_path_label.setStyleSheet("color: #aaa; padding: 4px;")
        engine_layout.addWidget(self.engine_path_label)

        engine_buttons = QHBoxLayout()
        self.btn_select_engine = QPushButton("Select Engine...")
        self.btn_select_engine.clicked.connect(self._select_engine)
        engine_buttons.addWidget(self.btn_select_engine)

        self.btn_reset_engine = QPushButton("Reset")
        self.btn_reset_engine.clicked.connect(self._reset_engine)
        engine_buttons.addWidget(self.btn_reset_engine)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["UCI", "XBoard"])
        engine_buttons.addWidget(QLabel("Protocol:"))
        engine_buttons.addWidget(self.protocol_combo)

        engine_layout.addLayout(engine_buttons)
        layout.addWidget(engine_group)

        pgn_group = QGroupBox("PGN Input")
        pgn_layout = QVBoxLayout(pgn_group)

        self.btn_load_pgn = QPushButton("Load PGN File...")
        self.btn_load_pgn.clicked.connect(self._load_pgn_file)
        pgn_layout.addWidget(self.btn_load_pgn)

        self.pgn_text = QTextEdit()
        self.pgn_text.setPlaceholderText("Paste PGN here...")
        self.pgn_text.setMaximumHeight(100)
        self.pgn_text.setStyleSheet("""
            QTextEdit { background-color: #1a1a1a; color: #ddd; border: 1px solid #444;
                        border-radius: 4px; padding: 4px; }
        """)
        pgn_layout.addWidget(self.pgn_text)

        pgn_buttons = QHBoxLayout()
        self.btn_parse_pgn = QPushButton("Load PGN")
        self.btn_parse_pgn.clicked.connect(self._parse_pgn)
        pgn_buttons.addWidget(self.btn_parse_pgn)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        pgn_buttons.addWidget(self.btn_clear)
        pgn_layout.addLayout(pgn_buttons)

        layout.addWidget(pgn_group)

        fen_group = QGroupBox("FEN Position")
        fen_layout = QHBoxLayout(fen_group)
        self.fen_input = QLineEdit()
        self.fen_input.setPlaceholderText("Enter FEN...")
        self.fen_input.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #444; border-radius: 4px; padding: 4px;")
        fen_layout.addWidget(self.fen_input)
        self.btn_load_fen = QPushButton("Set Position")
        self.btn_load_fen.clicked.connect(self._load_fen)
        fen_layout.addWidget(self.btn_load_fen)
        layout.addWidget(fen_group)

        move_group = QGroupBox("Manual Move")
        move_layout = QHBoxLayout(move_group)
        self.move_input_field = QLineEdit()
        self.move_input_field.setPlaceholderText("e.g., e2e4 or e4")
        self.move_input_field.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #444; border-radius: 4px; padding: 4px;")
        move_layout.addWidget(self.move_input_field)
        self.btn_send_move = QPushButton("Make Move")
        self.btn_send_move.clicked.connect(self._send_manual_move)
        move_layout.addWidget(self.btn_send_move)
        layout.addWidget(move_group)

        analysis_group = QGroupBox("Analysis")
        analysis_layout = QVBoxLayout(analysis_group)

        time_layout = QFormLayout()
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 60)
        self.time_spin.setValue(1)
        self.time_spin.setSuffix(" sec")
        self.time_spin.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #444; border-radius: 4px; padding: 2px;")
        time_layout.addRow("Time/move:", self.time_spin)
        analysis_layout.addLayout(time_layout)

        depth_layout = QFormLayout()
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(0, 99)
        self.depth_spin.setValue(0)
        self.depth_spin.setSpecialValueText("Auto")
        self.depth_spin.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #444; border-radius: 4px; padding: 2px;")
        depth_layout.addRow("Depth:", self.depth_spin)
        analysis_layout.addLayout(depth_layout)

        self.nnue_check = QCheckBox("Use NNUE")
        self.nnue_check.setChecked(False)
        self.nnue_check.setStyleSheet("color: #ccc;")
        analysis_layout.addWidget(self.nnue_check)

        analysis_buttons = QHBoxLayout()
        self.btn_start = QPushButton("Start Analysis")
        self.btn_start.clicked.connect(self._start_analysis)
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #2a6e3f; color: #fff; padding: 6px; border-radius: 4px; }
            QPushButton:hover { background-color: #3a8e5f; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        analysis_buttons.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.analysis_stopped.emit)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #8b3a3a; color: #fff; padding: 6px; border-radius: 4px; }
            QPushButton:hover { background-color: #b54a4a; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        analysis_buttons.addWidget(self.btn_stop)

        analysis_layout.addLayout(analysis_buttons)
        layout.addWidget(analysis_group)

        self.setStyleSheet("""
            QGroupBox { color: #ccc; border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding: 8px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 8px; }
            QPushButton { background-color: #333; color: #ccc; border: 1px solid #555; border-radius: 4px; padding: 4px 8px; }
            QPushButton:hover { background-color: #444; }
            QComboBox { background-color: #1a1a1a; color: #ddd; border: 1px solid #444; border-radius: 4px; padding: 2px; }
        """)

        layout.addStretch()

    def _select_engine(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Chess Engine", "",
            "Executables (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.engine_path = file_path
            name = Path(file_path).name
            self.engine_path_label.setText(name)

    def _reset_engine(self):
        self.engine_path = None
        self.engine_path_label.setText("Ember (default)")

    def _load_pgn_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PGN", "", "PGN Files (*.pgn);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.pgn_text.setText(content)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load PGN: {e}")

    def _parse_pgn(self):
        text = self.pgn_text.toPlainText().strip()
        if text:
            self.pgn_loaded.emit(text)

    def _load_fen(self):
        fen = self.fen_input.text().strip()
        if fen:
            self.fen_loaded.emit(fen)

    def _send_manual_move(self):
        move_str = self.move_input_field.text().strip()
        if move_str:
            self.move_input.emit(move_str)
            self.move_input_field.clear()

    def _start_analysis(self):
        self.analysis_started.emit("start")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def on_analysis_complete(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def get_engine_path(self, default: str = "Engines/Ember.exe") -> str:
        return self.engine_path or default

    def get_protocol(self) -> EngineProtocol:
        return EngineProtocol.UCI if self.protocol_combo.currentText() == "UCI" else EngineProtocol.XBOARD

    def get_time_per_move(self) -> int:
        return self.time_spin.value() * 1000

    def get_depth(self) -> Optional[int]:
        d = self.depth_spin.value()
        return d if d > 0 else None

    def get_nnue(self) -> bool:
        return self.nnue_check.isChecked()