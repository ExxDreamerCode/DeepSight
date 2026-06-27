from __future__ import annotations
from typing import Optional, List, Tuple, Dict

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPixmap, QFont

import chess

from .models.game_state import GameState, AnalyzedMove

LIGHT_SQ = QColor(240, 217, 181)
DARK_SQ = QColor(181, 136, 99)
LIGHT_SQ_HIGHLIGHT = QColor(245, 235, 100, 180)
DARK_SQ_HIGHLIGHT = QColor(245, 235, 100, 180)
LAST_MOVE_LIGHT = QColor(205, 210, 106, 180)
LAST_MOVE_DARK = QColor(170, 180, 80, 180)
ARROW_COLOR = QColor(0, 255, 0, 120)
ARROW_BORDER = QColor(0, 200, 0, 180)

class BoardWidget(QWidget):

    move_made = pyqtSignal(chess.Move)
    square_clicked = pyqtSignal(int)

    def __init__(self, game_state: GameState, parent=None):
        super().__init__(parent)
        self.game_state = game_state

        self._square_size = 60
        self.setMinimumSize(480, 480)

        self._pieces: Dict[str, QPixmap] = {}
        self._load_pieces()

        self._selected_square: Optional[int] = None
        self._legal_moves: List[chess.Move] = []

        self._arrow_from: Optional[int] = None
        self._arrow_to: Optional[int] = None

        self._last_move_squares: List[int] = []

        self.flipped = False

        self.setMouseTracking(True)

    def _load_pieces(self):
        pieces_dir = "Images/Pieces"
        piece_map = {
            'K': 'w_K.png', 'Q': 'w_Q.png', 'R': 'w_R.png',
            'B': 'w_B.png', 'N': 'w_N.png', 'P': 'w_P.png',
            'k': 'b_k.png', 'q': 'b_q.png', 'r': 'b_r.png',
            'b': 'b_b.png', 'n': 'b_n.png', 'p': 'b_p.png',
        }

        for symbol, filename in piece_map.items():
            try:
                path = f"{pieces_dir}/{filename}"
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self._pieces[symbol] = pixmap
            except Exception as e:
                print(f"Failed to load piece {filename}: {e}")

    def set_best_move_arrow(self, from_sq: Optional[int], to_sq: Optional[int]):

        self._arrow_from = from_sq
        self._arrow_to = to_sq
        self.update()

    def clear_arrow(self):
        self._arrow_from = None
        self._arrow_to = None
        self.update()

    def set_last_move(self, move: Optional[chess.Move]):

        if move:
            self._last_move_squares = [move.from_square, move.to_square]
        else:
            self._last_move_squares.clear()
        self.update()

    def flip_board(self):

        self.flipped = not self.flipped
        self.update()

    def square_coords(self, sq: int) -> Tuple[float, float]:

        file = chess.square_file(sq)
        rank = chess.square_rank(sq)

        if self.flipped:
            x = file * self._square_size
            y = rank * self._square_size
        else:
            x = (7 - file) * self._square_size
            y = (7 - rank) * self._square_size

        return x, y

    def screen_to_square(self, x: float, y: float) -> Optional[int]:

        file = int(x / self._square_size)
        rank = int(y / self._square_size)

        if not (0 <= file < 8 and 0 <= rank < 8):
            return None

        if self.flipped:
            return chess.square(file, rank)
        else:
            return chess.square(7 - file, 7 - rank)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        self._square_size = min(w, h) // 8

        board_offset_x = (w - self._square_size * 8) // 2
        board_offset_y = (h - self._square_size * 8) // 2

        painter.translate(board_offset_x, board_offset_y)

        for sq in range(64):
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)

            x, y = self.square_coords(sq)
            rect = QRectF(x, y, self._square_size, self._square_size)

            is_light = (file + rank) % 2 == 0
            color = LIGHT_SQ if is_light else DARK_SQ

            if sq in self._last_move_squares:
                color = LAST_MOVE_LIGHT if is_light else LAST_MOVE_DARK

            if sq == self._selected_square:
                color = LIGHT_SQ_HIGHLIGHT if is_light else DARK_SQ_HIGHLIGHT

            if any(m.to_square == sq for m in self._legal_moves):
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect)

                if self.game_state.board.piece_at(sq):

                    painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
                    painter.setPen(QPen(QColor(0, 0, 0, 60), 3))
                    painter.drawEllipse(rect.adjusted(4, 4, -4, -4))
                else:

                    painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    center = rect.center()
                    painter.drawEllipse(center, self._square_size * 0.15, self._square_size * 0.15)
                continue
            else:
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect)

        if self._arrow_from is not None and self._arrow_to is not None:
            self._draw_arrow(painter, self._arrow_from, self._arrow_to)

        for sq in range(64):
            piece = self.game_state.board.piece_at(sq)
            if piece is None:
                continue

            symbol = piece.symbol()
            if symbol in self._pieces:
                pixmap = self._pieces[symbol]
                x, y = self.square_coords(sq)

                scaled = pixmap.scaled(
                    self._square_size, self._square_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                offset_x = (self._square_size - scaled.width()) // 2
                offset_y = (self._square_size - scaled.height()) // 2

                painter.drawPixmap(int(x + offset_x), int(y + offset_y), scaled)

        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(0, 0, self._square_size * 8, self._square_size * 8)

    def _draw_arrow(self, painter: QPainter, from_sq: int, to_sq: int):

        import math

        x1, y1 = self.square_coords(from_sq)
        x2, y2 = self.square_coords(to_sq)

        cx1 = x1 + self._square_size / 2
        cy1 = y1 + self._square_size / 2
        cx2 = x2 + self._square_size / 2
        cy2 = y2 + self._square_size / 2

        p1 = QPointF(cx1, cy1)
        p2 = QPointF(cx2, cy2)

        painter.setPen(QPen(ARROW_BORDER, self._square_size * 0.25,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p1, p2)

        painter.setPen(QPen(ARROW_COLOR, self._square_size * 0.15,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p1, p2)

        dx = cx2 - cx1
        dy = cy2 - cy1
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)

        arrow_size = self._square_size * 0.35
        arrow_width = self._square_size * 0.25

        painter.setBrush(QBrush(ARROW_BORDER))
        painter.setPen(Qt.PenStyle.NoPen)

        painter.save()
        painter.translate(p2)
        painter.rotate(angle_deg)

        triangle = [
            QPointF(0, 0),
            QPointF(-arrow_size, -arrow_width / 2),
            QPointF(-arrow_size, arrow_width / 2)
        ]
        painter.drawPolygon(triangle)
        painter.restore()

    def mousePressEvent(self, event):

        if self.game_state.board.is_game_over():
            return

        x = event.position().x() - (self.width() - self._square_size * 8) // 2
        y = event.position().y() - (self.height() - self._square_size * 8) // 2

        sq = self.screen_to_square(x, y)
        if sq is None:
            return

        if self._selected_square is None:

            piece = self.game_state.board.piece_at(sq)
            if piece and piece.color == self.game_state.board.turn:
                self._selected_square = sq
                self._legal_moves = [
                    m for m in self.game_state.board.legal_moves
                    if m.from_square == sq
                ]
                self.update()
        else:

            move = chess.Move(self._selected_square, sq)

            if move.from_square and move.to_square:
                piece = self.game_state.board.piece_at(move.from_square)
                if piece and piece.piece_type == chess.PAWN:
                    promotion_rank = 7 if piece.color == chess.WHITE else 0
                    target_rank = chess.square_rank(move.to_square)
                    if target_rank == promotion_rank:
                        move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)

            if move in self.game_state.board.legal_moves:
                self._selected_square = None
                self._legal_moves.clear()
                self.move_made.emit(move)
            else:

                piece = self.game_state.board.piece_at(sq)
                if piece and piece.color == self.game_state.board.turn:
                    self._selected_square = sq
                    self._legal_moves = [
                        m for m in self.game_state.board.legal_moves
                        if m.from_square == sq
                    ]
                else:
                    self._selected_square = None
                    self._legal_moves.clear()

            self.update()

        self.square_clicked.emit(sq)
