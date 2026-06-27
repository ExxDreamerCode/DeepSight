from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient

import chess

class EvalBar(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(40)
        self.setMinimumHeight(200)

        self._score: Optional[float] = None
        self._mate: Optional[int] = None
        self._depth: int = 0

        self.white_color = QColor(240, 240, 240)
        self.black_color = QColor(40, 40, 40)
        self.arrow_color = QColor(180, 180, 180)

    def set_eval(self, score_cp: Optional[float] = None, mate: Optional[int] = None,
                 depth: int = 0):

        if mate is not None:
            self._mate = mate
            self._score = None
        else:
            self._score = score_cp / 100.0 if score_cp is not None else None
            self._mate = None
        self._depth = depth
        self.update()

    def clear(self):
        self._score = None
        self._mate = None
        self._depth = 0
        self.update()

    def _score_to_percent(self) -> float:

        if self._mate is not None:
            if self._mate > 0:
                return 1.0
            else:
                return 0.0

        if self._score is None:
            return 0.5

        import math
        prob = 1.0 / (1.0 + 10.0 ** (-self._score / 2.5))
        return max(0.0, min(1.0, prob))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        bar_rect = QRectF(5, 5, w - 10, h - 10)
        painter.setBrush(QBrush(self.black_color))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRoundedRect(bar_rect, 4, 4)

        white_percent = self._score_to_percent()
        white_height = int(bar_rect.height() * white_percent)

        if white_height > 0:
            white_rect = QRectF(
                bar_rect.x(),
                bar_rect.y(),
                bar_rect.width(),
                white_height
            )
            painter.setBrush(QBrush(self.white_color))
            painter.setPen(Qt.PenStyle.NoPen)

            path = self._round_top_rect(white_rect, 4)
            painter.drawPath(path)

        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawLine(
            int(bar_rect.x()),
            int(bar_rect.y() + white_height),
            int(bar_rect.x() + bar_rect.width()),
            int(bar_rect.y() + white_height)
        )

        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))

        eval_text = ""
        if self._mate is not None:
            eval_text = f"#{'−' if self._mate < 0 else ''}{abs(self._mate)}"
        elif self._score is not None:
            sign = "+" if self._score > 0 else ""
            eval_text = f"{sign}{self._score:.2f}"

        if eval_text:
            text_rect = QRectF(0, h - 30, w, 30)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter.value, eval_text)

        if self._depth > 0:
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QColor(200, 200, 200))
            depth_text = f"d={self._depth}"
            depth_rect = QRectF(0, h - 16, w, 16)
            painter.drawText(depth_rect, Qt.AlignmentFlag.AlignCenter.value, depth_text)

    def _round_top_rect(self, rect: QRectF, radius: float):

        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(rect.x(), rect.y() + radius)
        path.arcTo(rect.x(), rect.y(), radius * 2, radius * 2, 180, -90)
        path.lineTo(rect.x() + rect.width() - radius, rect.y())
        path.arcTo(rect.x() + rect.width() - radius * 2, rect.y(),
                   radius * 2, radius * 2, 90, -90)
        path.lineTo(rect.x() + rect.width(), rect.y() + rect.height())
        path.lineTo(rect.x(), rect.y() + rect.height())
        path.closeSubpath()
        return path
