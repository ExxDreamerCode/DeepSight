import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deepsight import __version__
from deepsight.self_check import build_report, summarize, write_report


def self_check_target(argv):
    index = argv.index("--self-check")
    if index + 1 < len(argv) and not argv[index + 1].startswith("-"):
        return argv[index + 1]
    return None


def run_self_check(argv) -> int:
    report = build_report()

    target = self_check_target(argv)
    if target:
        write_report(report, target)

    print(summarize(report))
    return 0 if report["ok"] else 1


def configure_dark_palette(app):
    from PyQt6.QtGui import QColor, QPalette

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(221, 221, 221))
    palette.setColor(QPalette.ColorRole.Base, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(34, 34, 34))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(51, 51, 51))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(221, 221, 221))
    palette.setColor(QPalette.ColorRole.Button, QColor(51, 51, 51))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(221, 221, 221))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(74, 158, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(110, 110, 110))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(110, 110, 110))
    app.setPalette(palette)


def main():
    if "--version" in sys.argv:
        print(f"DeepSight {__version__}")
        sys.exit(0)

    if "--self-check" in sys.argv:
        sys.exit(run_self_check(sys.argv))

    from PyQt6.QtWidgets import QApplication
    from deepsight.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("DeepSight")
    app.setApplicationVersion(__version__)

    app.setStyle("Fusion")
    configure_dark_palette(app)
    app.setStyleSheet("""
        QToolTip {
            background-color: #333;
            color: #fff;
            border: 1px solid #555;
            padding: 4px;
        }
    """)


    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
