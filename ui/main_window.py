# ui/main_window.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QHBoxLayout, QInputDialog, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from config.theme import ThemeManager
from core.engine import GameEngine
from core.save_manager import SaveInfo, SaveManager
from ui.dialogs import DebugMoneyDialog, NewGameDialog, ReportDialog
from ui.navigation import NavigationItem, SidebarNavigation
from ui.pages import ContentArea
from ui.time_bar import TimeControlBar


class MainWindow(QMainWindow):
    def __init__(
        self,
        engine: GameEngine,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._theme_manager = theme_manager
        self._save_manager = SaveManager()
        self._report_dialogs: list[ReportDialog] = []

        self.setWindowTitle("Property Empire Simulator")
        self.resize(1440, 900)
        self._build_menu()

        self._time_bar = TimeControlBar(engine=self._engine, theme_manager=self._theme_manager)
        self._content_area = ContentArea(engine=self._engine)
        self._sidebar = SidebarNavigation(
            items=(
                NavigationItem(key="dashboard", label="Dashboard"),
                NavigationItem(key="deals", label="Deals"),
                NavigationItem(key="portfolio", label="Portfolio"),
                NavigationItem(key="managers", label="City Managers"),
                NavigationItem(key="development", label="Land & Development"),
                NavigationItem(key="finance", label="Finance & Tax"),
                NavigationItem(key="cities", label="Cities"),
                NavigationItem(key="credit", label="Credit & Loans"),
                NavigationItem(key="reports", label="Reports"),
                NavigationItem(key="research", label="Research"),
                NavigationItem(key="competitors", label="Competitors"),
                NavigationItem(key="settings", label="Settings"),
            )
        )
        self._sidebar.section_changed.connect(self._content_area.show_page)

        shell = QWidget()
        shell_layout = QVBoxLayout()
        shell_layout.setContentsMargins(6, 6, 6, 6)
        shell_layout.setSpacing(6)
        shell.setLayout(shell_layout)

        body = QWidget()
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)
        body.setLayout(body_layout)

        body_layout.addWidget(self._sidebar)
        body_layout.addWidget(self._content_area, stretch=1)

        shell_layout.addWidget(self._time_bar)
        shell_layout.addWidget(body, stretch=1)

        self.setCentralWidget(shell)
        self.statusBar().showMessage(f"Theme: {self._theme_manager.active_theme.name}")

        self._timer = QTimer(self)
        self._timer.setInterval(650)
        self._timer.timeout.connect(self._advance_simulation)
        self._timer.start()
        self._money_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self._money_shortcut.activated.connect(self._open_money_menu)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("New Game", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_game)
        file_menu.addAction(new_action)

        save_action = QAction("Save Game", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_game)
        file_menu.addAction(save_action)

        load_action = QAction("Load Game", self)
        load_action.setShortcut(QKeySequence.StandardKey.Open)
        load_action.triggered.connect(self._load_game)
        file_menu.addAction(load_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _advance_simulation(self) -> None:
        self._engine.tick()
        self._time_bar.refresh()
        self._content_area.refresh_live()
        for report in self._engine.gameplay.pop_pending_reports(self._engine.state):
            if not bool(self._engine.state.metadata.get("setting_show_report_popups", True)):
                continue
            dialog = ReportDialog(report, self)
            dialog.finished.connect(lambda _result, shown=dialog: self._forget_report(shown))
            self._report_dialogs.append(dialog)
            dialog.show()

    def _forget_report(self, dialog: ReportDialog) -> None:
        if dialog in self._report_dialogs:
            self._report_dialogs.remove(dialog)

    def _open_money_menu(self) -> None:
        if not bool(self._engine.state.metadata.get("setting_developer_money_enabled", True)):
            self.statusBar().showMessage("Developer money menu disabled in Settings.")
            return
        dialog = DebugMoneyDialog(self)
        if dialog.exec():
            try:
                self._engine.gameplay.grant_debug_cash(self._engine.state, dialog.amount)
            except ValueError as exc:
                QMessageBox.warning(self, "Money unavailable", str(exc))
                return
            self._time_bar.refresh()
            self._content_area.refresh()

    def _new_game(self) -> None:
        dialog = NewGameDialog(self._engine.state.world, self)
        if not dialog.exec():
            return
        self._engine.state = self._engine.gameplay.new_game(
            dialog.company_name,
            dialog.starting_industry,
            dialog.hq_city_id,
        )
        self._time_bar.refresh()
        self._content_area.refresh()
        self.statusBar().showMessage("New game started.")

    def _save_game(self) -> None:
        slot_name, accepted = QInputDialog.getText(self, "Save Game", "Save name", text="autosave")
        if not accepted:
            return
        try:
            path = self._save_manager.save_world(self._engine.state, slot_name.strip() or "autosave")
        except ValueError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        self.statusBar().showMessage(f"Saved: {path}")

    def _load_game(self) -> None:
        saves = self._available_saves()
        if not saves:
            QMessageBox.information(self, "No saves found", "No saved games are available yet.")
            return
        labels = [
            f"{save.world_id} / {save.slot_name} - {save.saved_at[:19].replace('T', ' ')}"
            for save in saves
        ]
        selected, accepted = QInputDialog.getItem(self, "Load Game", "Saved game", labels, 0, False)
        if not accepted or selected not in labels:
            return
        save = saves[labels.index(selected)]
        try:
            self._engine.state = self._save_manager.load_world(save.world_id, save.slot_name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Load failed", str(exc))
            return
        self._time_bar.refresh()
        self._content_area.refresh()
        self.statusBar().showMessage(f"Loaded: {save.world_id} / {save.slot_name}")

    def _available_saves(self) -> list[SaveInfo]:
        saves: list[SaveInfo] = []
        for world_id in self._save_manager.list_worlds():
            saves.extend(self._save_manager.list_saves(world_id))
        return sorted(saves, key=lambda save: save.saved_at, reverse=True)
