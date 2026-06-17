# main.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from config.theme import ThemeManager
from core.engine import GameEngine
from ui.main_window import MainWindow


def build_engine() -> GameEngine:
    """Create the simulation layer without importing UI concerns."""
    return GameEngine()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Property Empire Simulator")
    app.setOrganizationName("Platinum")

    theme_manager = ThemeManager.default()
    app.setStyleSheet(theme_manager.current_stylesheet())

    window = MainWindow(engine=build_engine(), theme_manager=theme_manager)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
