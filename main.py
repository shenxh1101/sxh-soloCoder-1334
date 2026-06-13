import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from database import Database
from audio import ensure_sound_files
from pomodoro import PomodoroWindow


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    ensure_sound_files()
    db = Database()
    window = PomodoroWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
