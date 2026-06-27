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
