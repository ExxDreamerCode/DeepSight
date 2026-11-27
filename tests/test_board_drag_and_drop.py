from __future__ import annotations

import chess
import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QtGui = pytest.importorskip("PyQt6.QtGui")
QtCore = pytest.importorskip("PyQt6.QtCore")


@pytest.fixture(scope="module")
def app():
    try:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    except Exception as exc:
        pytest.skip(f"no GUI platform available: {exc}")
    return app


@pytest.fixture
def board(app):
    from deepsight.board_widget import BoardWidget
    from deepsight.models.game_state import GameState

    widget = BoardWidget(GameState())
    widget.resize(480, 480)
    widget.show()
    for _ in range(5):
        app.processEvents()
    yield widget
    widget.hide()


def _mouse_event(event_type, pos, button):
    modifiers = QtCore.Qt.KeyboardModifier.NoModifier
    try:
        return QtGui.QMouseEvent(
            event_type, pos, pos, pos, button, button, modifiers
        )
    except TypeError:
        return QtGui.QMouseEvent(
            event_type, pos, pos, button, button, modifiers
        )


def _center_of_square(widget, sq):
    board_x, board_y, _ = widget._board_geometry()
    sx, sy = widget.square_coords(sq)
    return QtCore.QPointF(
        board_x + sx + widget._square_size / 2,
        board_y + sy + widget._square_size / 2,
    )


def _drag(board, from_sq, to_sq):
    press_pos = _center_of_square(board, from_sq)
    release_pos = _center_of_square(board, to_sq)
    board.mousePressEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonPress, press_pos, QtCore.Qt.MouseButton.LeftButton)
    )
    board.mouseMoveEvent(
        _mouse_event(QtCore.QEvent.Type.MouseMove, release_pos, QtCore.Qt.MouseButton.LeftButton)
    )
    board.mouseReleaseEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonRelease, release_pos, QtCore.Qt.MouseButton.LeftButton)
    )


def _capture_moves(board):
    moves = []
    board.move_made.connect(moves.append)
    return moves


def test_dragging_lifts_piece_and_follows_cursor(board):
    press_pos = _center_of_square(board, chess.E2)
    board.mousePressEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonPress, press_pos, QtCore.Qt.MouseButton.LeftButton)
    )
    assert board._drag_active
    assert board._drag_from == chess.E2

    target = _center_of_square(board, chess.E4)
    board.mouseMoveEvent(
        _mouse_event(QtCore.QEvent.Type.MouseMove, target, QtCore.Qt.MouseButton.LeftButton)
    )
    assert board._drag_target == chess.E4


def test_drag_to_legal_square_emits_move(board, app):
    moves = _capture_moves(board)
    _drag(board, chess.E2, chess.E4)
    app.processEvents()

    assert len(moves) == 1
    assert moves[0] == chess.Move(chess.E2, chess.E4)


def test_drag_promotes_pawn_to_queen(board, app):
    board.game_state.board = chess.Board("4k3/3P4/8/8/8/8/8/4K3 w - - 0 1")
    moves = _capture_moves(board)
    _drag(board, chess.D7, chess.D8)
    app.processEvents()

    assert len(moves) == 1
    assert moves[0] == chess.Move(chess.D7, chess.D8, promotion=chess.QUEEN)


def test_drag_capture(board, app):
    board.game_state.board = chess.Board("8/8/4p3/3P4/8/8/8/8 w - - 0 1")
    moves = _capture_moves(board)
    _drag(board, chess.D5, chess.E6)
    app.processEvents()

    assert len(moves) == 1
    assert moves[0] == chess.Move(chess.D5, chess.E6)


def test_drag_to_illegal_square_snaps_back(board, app):
    moves = _capture_moves(board)
    _drag(board, chess.E2, chess.F3)
    app.processEvents()

    assert len(moves) == 0
    assert board.game_state.board.piece_at(chess.E2) is not None
    assert board._drag_from is None


def test_drag_off_board_snaps_back(board, app):
    moves = _capture_moves(board)
    press_pos = _center_of_square(board, chess.E2)
    board.mousePressEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonPress, press_pos, QtCore.Qt.MouseButton.LeftButton)
    )
    outside = QtCore.QPointF(-100, -100)
    board.mouseMoveEvent(
        _mouse_event(QtCore.QEvent.Type.MouseMove, outside, QtCore.Qt.MouseButton.LeftButton)
    )
    board.mouseReleaseEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonRelease, outside, QtCore.Qt.MouseButton.LeftButton)
    )
    app.processEvents()

    assert len(moves) == 0
    assert board.game_state.board.piece_at(chess.E2) is not None
    assert not board._drag_active


def test_drag_enemy_piece_while_white_to_move_does_nothing(board, app):
    moves = _capture_moves(board)
    _drag(board, chess.E7, chess.E5)
    app.processEvents()

    assert len(moves) == 0
    assert board._drag_from is None


def test_tap_selects_piece_and_second_tap_moves(board, app):
    moves = _capture_moves(board)
    e2 = _center_of_square(board, chess.E2)
    board.mousePressEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonPress, e2, QtCore.Qt.MouseButton.LeftButton)
    )
    board.mouseReleaseEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonRelease, e2, QtCore.Qt.MouseButton.LeftButton)
    )
    app.processEvents()

    assert len(moves) == 0
    assert board._selected_square == chess.E2
    assert board._legal_moves

    e4 = _center_of_square(board, chess.E4)
    board.mousePressEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonPress, e4, QtCore.Qt.MouseButton.LeftButton)
    )
    board.mouseReleaseEvent(
        _mouse_event(QtCore.QEvent.Type.MouseButtonRelease, e4, QtCore.Qt.MouseButton.LeftButton)
    )
    app.processEvents()

    assert len(moves) == 1
    assert moves[0] == chess.Move(chess.E2, chess.E4)


def test_game_over_blocks_drag(board, app):
    moves = _capture_moves(board)
    b = board.game_state.board
    b.push(chess.Move.from_uci("f2f3"))
    b.push(chess.Move.from_uci("e7e5"))
    b.push(chess.Move.from_uci("g2g4"))
    b.push(chess.Move.from_uci("d8h4"))
    assert b.is_game_over()

    _drag(board, chess.E2, chess.E4)
    app.processEvents()

    assert len(moves) == 0
    assert not board._drag_active
