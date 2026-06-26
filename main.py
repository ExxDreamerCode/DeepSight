import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from deepsight.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DeepSight")

    app.setStyle("Fusion")
    app.setStyleSheet("""
        QToolTip {
            background:
            color:
            border: 1px solid
            padding: 4px;
        }
    """)

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
