from __future__ import annotations

import pytest

PANEL_WIDTH = 312
MIN_ANALYSIS_BUTTON_HEIGHT = 28


@pytest.fixture(scope="module")
def panel():
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    QtGui = pytest.importorskip("PyQt6.QtGui")
    try:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    except Exception as exc:
        pytest.skip(f"no GUI platform available: {exc}")

    if not QtGui.QFontDatabase.families():
        pytest.skip("no fonts are installed, widget geometry is meaningless")

    from deepsight.input_panel import InputPanel
    from deepsight.models.game_state import GameState

    widget = InputPanel(GameState())
    widget.setFixedWidth(PANEL_WIDTH)
    widget.show()
    for _ in range(5):
        app.processEvents()
    yield widget
    widget.hide()


def test_analysis_buttons_are_tall_enough_to_look_like_buttons(panel):
    for button in (panel.btn_start, panel.btn_stop, panel.btn_flip):
        assert button.height() >= MIN_ANALYSIS_BUTTON_HEIGHT, (
            f"{button.text()!r} is only {button.height()}px tall"
        )
        assert button.height() > panel.btn_load_pgn.height()


def test_analysis_buttons_share_one_row(panel):
    layout = panel.btn_start.parent().layout()
    rows = [layout.itemAt(i).layout() for i in range(layout.count())]

    shared = [row for row in rows if row is not None and row.indexOf(panel.btn_start) >= 0]
    assert len(shared) == 1
    assert shared[0].indexOf(panel.btn_stop) >= 0
    assert shared[0].indexOf(panel.btn_flip) >= 0


def test_analysis_buttons_have_room_for_their_labels(panel):
    for button in (panel.btn_start, panel.btn_stop, panel.btn_flip):
        text = button.fontMetrics().horizontalAdvance(button.text())
        assert button.width() >= 60, f"{button.text()!r} shrank to {button.width()}px"
        assert button.width() >= text + 16, f"{button.text()!r} is crammed into {button.width()}px"


def test_analysis_group_is_not_squeezed(panel):
    group = panel.btn_start.parent()
    assert group.width() >= group.minimumSizeHint().width()
    assert group.height() >= group.sizeHint().height()


def test_analysis_fields_use_the_available_width(panel):
    for field in (panel.time_spin, panel.depth_spin):
        assert field.width() >= 180, f"{type(field).__name__} is only {field.width()}px wide"


def test_skip_checkbox_fits_the_panel_width(panel):
    assert panel.skip_analyzed_check.minimumSizeHint().width() <= PANEL_WIDTH


def test_skip_checkbox_is_on_by_default(panel):
    assert panel.skip_analyzed_check.isChecked()
    assert panel.get_skip_analyzed() is True

    panel.skip_analyzed_check.setChecked(False)
    try:
        assert panel.get_skip_analyzed() is False
    finally:
        panel.skip_analyzed_check.setChecked(True)
