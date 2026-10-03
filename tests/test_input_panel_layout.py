from __future__ import annotations

import pytest

PANEL_WIDTH = 312
PANEL_HEIGHT = 830
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
    widget.resize(PANEL_WIDTH, PANEL_HEIGHT)
    widget.show()
    for _ in range(5):
        app.processEvents()
    yield widget
    widget.hide()


def test_analysis_buttons_are_tall_enough_to_look_like_buttons(panel):
    reference = panel.btn_load_pgn.height()
    for button in (panel.btn_start, panel.btn_stop, panel.btn_flip):
        assert button.height() >= MIN_ANALYSIS_BUTTON_HEIGHT, (
            f"{button.text()!r} is only {button.height()}px tall"
        )
        assert button.height() >= reference


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


def test_nothing_is_squeezed_at_the_default_panel_size(panel):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

    assert panel.minimumSizeHint().height() <= PANEL_HEIGHT
    assert panel.minimumSizeHint().width() <= PANEL_WIDTH

    for group in panel.findChildren(QtWidgets.QGroupBox):
        assert group.height() >= group.minimumSizeHint().height(), f"{group.title()} is squeezed"
        assert group.width() >= group.minimumSizeHint().width(), f"{group.title()} is squeezed"


def test_analysis_fields_use_the_available_width(panel):
    for field in (panel.time_spin, panel.depth_spin):
        assert field.width() >= 160, f"{type(field).__name__} is only {field.width()}px wide"
        assert field.width() > field.sizeHint().width(), (
            f"{type(field).__name__} hugs its contents instead of filling the row"
        )


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
