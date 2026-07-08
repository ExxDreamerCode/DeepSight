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
CHECK_COLOR = QColor(245, 145, 45)
CHECKMATE_COLOR = QColor(220, 45, 45)
BOARD_BG = QColor(26, 26, 26)
COORD_COLOR = QColor(190, 190, 190)
COORD_MARGIN = 22
CAPTURE_MARGIN = 30
PIECE_ORDER = {
    chess.QUEEN: 0,
    chess.ROOK: 1,
    chess.BISHOP: 2,
    chess.KNIGHT: 3,
    chess.PAWN: 4,
}

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
        from .engine_registry import get_data_path
        pieces_dir = get_data_path("Images/Pieces")
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
            x = (7 - file) * self._square_size
            y = rank * self._square_size
        else:
            x = file * self._square_size
            y = (7 - rank) * self._square_size

        return x, y

    def screen_to_square(self, x: float, y: float) -> Optional[int]:

        file = int(x / self._square_size)
        rank = int(y / self._square_size)

        if not (0 <= file < 8 and 0 <= rank < 8):
            return None

        if self.flipped:
            return chess.square(7 - file, rank)
        return chess.square(file, 7 - rank)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), BOARD_BG)

        board_offset_x, board_offset_y, board_size = self._board_geometry()

        self._draw_captured_pieces(painter, board_offset_x, board_offset_y, board_size)
        self._draw_coordinates(painter, board_offset_x, board_offset_y, board_size)

        painter.save()
        painter.translate(board_offset_x, board_offset_y)

        for sq in range(64):
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)

            x, y = self.square_coords(sq)
            rect = QRectF(x, y, self._square_size, self._square_size)

            is_light = (file + rank) % 2 == 1
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

        self._draw_check_marker(painter)

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
        painter.restore()

    def _board_geometry(self) -> Tuple[int, int, int]:
        vertical_margin = COORD_MARGIN + CAPTURE_MARGIN
        usable_width = max(8, self.width() - COORD_MARGIN * 2)
        usable_height = max(8, self.height() - vertical_margin * 2)
        self._square_size = max(1, min(usable_width, usable_height) // 8)
        board_size = self._square_size * 8
        board_offset_x = (self.width() - board_size) // 2
        board_offset_y = (self.height() - board_size) // 2
        return board_offset_x, board_offset_y, board_size

    def _square_at_board_cell(self, col: int, row: int) -> int:
        if self.flipped:
            return chess.square(7 - col, row)
        return chess.square(col, 7 - row)

    def _draw_coordinates(self, painter: QPainter, board_x: int, board_y: int,
                          board_size: int):
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(COORD_COLOR)

        for col in range(8):
            sq = self._square_at_board_cell(col, 0)
            label = chess.FILE_NAMES[chess.square_file(sq)]
            x = board_x + col * self._square_size
            painter.drawText(
                QRectF(x, board_y - COORD_MARGIN, self._square_size, COORD_MARGIN),
                Qt.AlignmentFlag.AlignCenter.value,
                label
            )
            painter.drawText(
                QRectF(x, board_y + board_size, self._square_size, COORD_MARGIN),
                Qt.AlignmentFlag.AlignCenter.value,
                label
            )

        for row in range(8):
            sq = self._square_at_board_cell(0, row)
            label = str(chess.square_rank(sq) + 1)
            y = board_y + row * self._square_size
            painter.drawText(
                QRectF(board_x - COORD_MARGIN, y, COORD_MARGIN, self._square_size),
                Qt.AlignmentFlag.AlignCenter.value,
                label
            )
            painter.drawText(
                QRectF(board_x + board_size, y, COORD_MARGIN, self._square_size),
                Qt.AlignmentFlag.AlignCenter.value,
                label
            )

    def _draw_captured_pieces(self, painter: QPainter, board_x: int, board_y: int,
                              board_size: int):
        captured = self._captured_pieces_by_side()
        top_side = chess.WHITE if self.flipped else chess.BLACK
        bottom_side = chess.BLACK if self.flipped else chess.WHITE

        top_rect = QRectF(
            board_x,
            board_y - COORD_MARGIN - CAPTURE_MARGIN,
            board_size,
            CAPTURE_MARGIN
        )
        bottom_rect = QRectF(
            board_x,
            board_y + board_size + COORD_MARGIN,
            board_size,
            CAPTURE_MARGIN
        )

        self._draw_captured_row(painter, top_rect, captured[top_side])
        self._draw_captured_row(painter, bottom_rect, captured[bottom_side])

    def _captured_pieces_by_side(self) -> Dict[chess.Color, List[chess.Piece]]:
        captured: Dict[chess.Color, List[chess.Piece]] = {
            chess.WHITE: [],
            chess.BLACK: [],
        }

        if self.game_state.current_move_index < 0:
            return captured

        board = chess.Board()
        try:
            board.set_fen(self.game_state._initial_fen)
        except Exception:
            return captured

        for index, analyzed_move in enumerate(self.game_state.moves):
            if index > self.game_state.current_move_index:
                break

            move = analyzed_move.move
            if move not in board.legal_moves:
                break

            moving_side = board.turn
            if board.is_en_passant(move):
                taken_piece = chess.Piece(chess.PAWN, not moving_side)
            else:
                taken_piece = board.piece_at(move.to_square)

            if taken_piece is not None:
                captured[moving_side].append(taken_piece)

            board.push(move)

        return captured

    def _material_balance(self) -> str:
        captured = self._captured_pieces_by_side()
        
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }
        
        white_material = sum(piece_values.get(p.piece_type, 0) for p in captured[chess.WHITE])
        black_material = sum(piece_values.get(p.piece_type, 0) for p in captured[chess.BLACK])
        
        diff = white_material - black_material
        
        if diff > 0:
            return f"+{diff}"
        elif diff < 0:
            return str(diff)
        return "0"

    def _draw_captured_row(self, painter: QPainter, rect: QRectF,
                           pieces: List[chess.Piece]):
        if not pieces:
            return

        pieces = sorted(
            pieces,
            key=lambda piece: PIECE_ORDER.get(piece.piece_type, len(PIECE_ORDER))
        )
        icon_size = min(CAPTURE_MARGIN - 4, int(rect.width()) // len(pieces))
        icon_size = max(10, icon_size)
        spacing = 2 if icon_size * len(pieces) + 2 * (len(pieces) - 1) <= rect.width() else 0
        total_width = icon_size * len(pieces) + spacing * (len(pieces) - 1)
        x = rect.x() + 2
        if total_width > rect.width():
            x = rect.x()
        y = rect.y() + (rect.height() - icon_size) / 2

        for piece in pieces:
            pixmap = self._pieces.get(piece.symbol())
            if pixmap is None:
                painter.setPen(COORD_COLOR)
                painter.drawText(
                    QRectF(x, y, icon_size, icon_size),
                    Qt.AlignmentFlag.AlignCenter.value,
                    piece.symbol()
                )
            else:
                scaled = pixmap.scaled(
                    icon_size,
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                offset_x = (icon_size - scaled.width()) // 2
                offset_y = (icon_size - scaled.height()) // 2
                painter.drawPixmap(
                    int(x + offset_x),
                    int(y + offset_y),
                    scaled
                )
            x += icon_size + spacing

    def material_label_text(self) -> str:
        return self._material_balance()

    def _draw_check_marker(self, painter: QPainter):
        board = self.game_state.board
        if not board.is_check():
            return

        king_square = board.king(board.turn)
        if king_square is None:
            return

        color = CHECKMATE_COLOR if board.is_checkmate() else CHECK_COLOR
        fill = QColor(color)
        fill.setAlpha(85)
        border = QColor(color)
        border.setAlpha(230)

        x, y = self.square_coords(king_square)
        margin = self._square_size * 0.12
        rect = QRectF(
            x + margin,
            y + margin,
            self._square_size - margin * 2,
            self._square_size - margin * 2
        )

        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, max(3, int(self._square_size * 0.06))))
        painter.drawEllipse(rect)

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

        board_offset_x, board_offset_y, _ = self._board_geometry()
        x = event.position().x() - board_offset_x
        y = event.position().y() - board_offset_y

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
