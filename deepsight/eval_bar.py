from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient

import chess

class EvalBar(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(52)
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
        painter.fillRect(self.rect(), QColor(26, 26, 26))

        eval_text = self._eval_text()

        has_text = bool(eval_text) or self._depth > 0
        text_area_height = 42 if has_text else 0
        bar_rect = QRectF(5, 5, w - 10, max(20, h - text_area_height - 10))
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

        if has_text:
            label_rect = QRectF(2, h - text_area_height + 3, w - 4, text_area_height - 6)
            painter.setBrush(QBrush(QColor(18, 18, 18)))
            painter.setPen(QPen(QColor(55, 55, 55), 1))
            painter.drawRoundedRect(label_rect, 4, 4)

        if eval_text:
            text_rect = QRectF(3, h - text_area_height + 5, w - 6, 19)
            font = self._fitted_font(painter, QFont("Segoe UI", 10, QFont.Weight.Bold),
                                     eval_text, int(text_rect.width()))
            painter.setFont(font)
            painter.setPen(QColor(245, 245, 245))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter.value, eval_text)

        if self._depth > 0:
            depth_text = f"d={self._depth}"
            depth_rect = QRectF(3, h - text_area_height + 24, w - 6, 15)
            font = self._fitted_font(painter, QFont("Segoe UI", 8), depth_text,
                                     int(depth_rect.width()))
            painter.setFont(font)
            painter.setPen(QColor(190, 190, 190))
            painter.drawText(depth_rect, Qt.AlignmentFlag.AlignCenter.value, depth_text)

    def _fitted_font(self, painter: QPainter, font: QFont, text: str, max_width: int) -> QFont:
        fitted = QFont(font)
        while fitted.pointSize() > 6:
            painter.setFont(fitted)
            if painter.fontMetrics().horizontalAdvance(text) <= max_width:
                break
            fitted.setPointSize(fitted.pointSize() - 1)
        return fitted

    def _eval_text(self) -> str:
        if self._mate is not None:
            if self._mate == 0 or (self._depth == 0 and abs(self._mate) == 1):
                return "#0"
            return f"#{'-' if self._mate < 0 else ''}{abs(self._mate)}"

        if self._score is not None:
            sign = "+" if self._score > 0 else ""
            return f"{sign}{self._score:.2f}"

        return ""

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
