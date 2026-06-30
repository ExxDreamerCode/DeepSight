from __future__ import annotations
from typing import Optional, Dict, List
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QFrame, QSizePolicy, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QKeyEvent

import chess

from .models.game_state import GameState, AnalyzedMove

class MoveCell(QFrame):

    clicked = pyqtSignal(int)

    def __init__(self, move: Optional[AnalyzedMove], move_index: int, parent=None):
        super().__init__(parent)
        self.move = move
        self.move_index = move_index
        self._selected = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("MoveCell:hover { background-color: #3a3a3a; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)

        if move is None:
            label = QLabel("")
            label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(label)
        else:
            icon_label = IconLabel(move.classification)
            icon_label.setFixedSize(18, 18)
            layout.addWidget(icon_label)

            move_label = QLabel(move.san)
            move_label.setFont(QFont("Segoe UI", 10))
            c = "#fff" if move.player == chess.WHITE else "#ddd"
            move_label.setStyleSheet(f"color: {c};")
            layout.addWidget(move_label)

            ev = move.eval_after or move.eval_before
            if ev:

                is_after = move.eval_after is not None
                if is_after:
                    invert = move.player == chess.WHITE
                else:
                    invert = move.player == chess.BLACK

                if ev.score_cp is not None:
                    score = ev.score_cp
                    if invert:
                        score = -score
                    display = f"{score / 100.0:+.2f}"
                elif ev.mate is not None:
                    mate = ev.mate
                    if invert:
                        mate = -mate
                    display = f"#{'+' if mate > 0 else ''}{mate}"
                else:
                    display = ""
                if display:
                    el = QLabel(display)
                    el.setFont(QFont("Segoe UI", 9))
                    el.setStyleSheet("color: #aaa;")
                    layout.addWidget(el)

            if move.depth > 0:
                dl = QLabel(f"d{move.depth}")
                dl.setFont(QFont("Segoe UI", 8))
                dl.setStyleSheet("color: #666;")
                layout.addWidget(dl)

            layout.addStretch()

        self.setFixedHeight(32)

    def set_selected(self, sel: bool):
        self._selected = sel
        if sel:
            self.setStyleSheet("MoveCell { background-color: #4a4a4a; }")
        else:
            self.setStyleSheet("MoveCell:hover { background-color: #3a3a3a; }")

    def mousePressEvent(self, event):
        if self.move is not None:
            self.clicked.emit(self.move_index)

class MoveRow(QFrame):

    cell_clicked = pyqtSignal(int)

    def __init__(self, move_number: int, white_move: Optional[AnalyzedMove] = None,
                 black_move: Optional[AnalyzedMove] = None, parent=None):
        super().__init__(parent)
        self.move_number = move_number
        self.white_move = white_move
        self.black_move = black_move

        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(4)

        self.num_label = QLabel(f"{move_number}.")
        self.num_label.setFixedWidth(30)
        font = QFont("Segoe UI", 10)
        self.num_label.setFont(font)
        self.num_label.setStyleSheet("color: #888;")
        layout.addWidget(self.num_label)

        wi = (move_number - 1) * 2
        wc = MoveCell(white_move, wi)
        wc.clicked.connect(self.cell_clicked.emit)
        layout.addWidget(wc, 1)
        self.white_cell = wc

        bi = wi + 1 if black_move else -1
        bc = MoveCell(black_move, bi)
        if black_move:
            bc.clicked.connect(self.cell_clicked.emit)
        layout.addWidget(bc, 1)
        self.black_cell = bc

        self.setFixedHeight(34)

    def select_cell(self, move_index: int):

        self.white_cell.set_selected(self.white_cell.move_index == move_index)
        self.black_cell.set_selected(self.black_cell.move_index == move_index)

class IconLabel(QLabel):

    _icons: Dict[str, QPixmap] = {}

    def __init__(self, classification: str, parent=None):
        super().__init__(parent)
        self.classification = classification
        if not IconLabel._icons:
            self._load_icons()
        if classification in IconLabel._icons:
            self.setPixmap(IconLabel._icons[classification].scaled(
                16, 16, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.setText("")

    @classmethod
    def _load_icons(cls):
        moves_dir = Path("Images/Moves")
        if moves_dir.exists():
            for icon_file in moves_dir.glob("*.svg"):
                name = icon_file.stem
                pixmap = QPixmap(str(icon_file))
                if not pixmap.isNull():
                    cls._icons[name] = pixmap

class MoveListPanel(QScrollArea):

    move_selected = pyqtSignal(int)
    navigation_requested = pyqtSignal(str)

    def __init__(self, game_state: GameState, parent=None):
        super().__init__(parent)
        self.game_state = game_state
        self._rows: List[MoveRow] = []
        self._selected_index: int = -1

        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addStretch()

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { background-color: #1a1a1a; border: none; }
            QScrollBar:vertical { background: #222; width: 8px; }
            QScrollBar::handle:vertical { background: #555; border-radius: 4px; }
        """)

        self._build_list()

    def _build_list(self):
        for row in self._rows:
            self.layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        moves = self.game_state.moves
        if not moves:
            empty_label = QLabel("No moves")
            empty_label.setStyleSheet("color: #666; padding: 20px;")
            self.layout.insertWidget(self.layout.count() - 1, empty_label)
            self._rows.append(empty_label)
            return

        i = 0
        while i < len(moves):
            if moves[i].player == chess.WHITE:
                white = moves[i]
                black = moves[i + 1] if i + 1 < len(moves) and moves[i + 1].player == chess.BLACK else None
                row = MoveRow(len(self._rows) + 1, white, black)
                self._rows.append(row)
                i += 2 if black else 1
            else:
                row = MoveRow(len(self._rows) + 1, None, moves[i])
                self._rows.append(row)
                i += 1

        for row in self._rows:
            if isinstance(row, MoveRow):
                row.cell_clicked.connect(self._on_cell_clicked)
                self.layout.insertWidget(self.layout.count() - 1, row)

    def _on_cell_clicked(self, move_index: int):
        if move_index < 0 or move_index >= len(self.game_state.moves):
            return
        self._select_move(move_index)

    def _select_move(self, move_index: int, emit_signal: bool = True):
        if move_index < 0 or move_index >= len(self.game_state.moves):
            return
        self._selected_index = move_index

        for row in self._rows:
            if isinstance(row, MoveRow):
                row.select_cell(-1)

        for row in self._rows:
            if isinstance(row, MoveRow):
                if row.white_cell.move_index == move_index:
                    row.select_cell(move_index)
                    break
                if row.black_cell.move_index == move_index:
                    row.select_cell(move_index)
                    break

        if emit_signal:
            self.move_selected.emit(move_index)

    def refresh(self, emit_signal: bool = False, select_index: Optional[int] = None):
        if select_index is not None:
            idx_to_select = select_index
        else:
            idx_to_select = self._selected_index

        # Сохраняем позицию скролла
        scroll_pos = self.verticalScrollBar().value()

        self._build_list()

        if 0 <= idx_to_select < len(self.game_state.moves):
            self._select_move(idx_to_select, emit_signal=emit_signal)
            self.scroll_to_move(idx_to_select)
        else:
            self.verticalScrollBar().setValue(scroll_pos)

    def scroll_to_move(self, move_index: int):
        for row in self._rows:
            if isinstance(row, MoveRow):
                if row.white_cell.move_index == move_index or row.black_cell.move_index == move_index:
                    self.ensureWidgetVisible(row)
                    break

    def keyPressEvent(self, event: QKeyEvent):

        if event.key() == Qt.Key.Key_Left:
            self.navigation_requested.emit("back")
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            self.navigation_requested.emit("forward")
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            self.navigation_requested.emit("start")
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            self.navigation_requested.emit("end")
            event.accept()
        else:
            super().keyPressEvent(event)
