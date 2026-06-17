# ui/time_bar.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from config.theme import ThemeManager
from core.clock import GameSpeed
from core.engine import GameEngine


def _money(value: int | float) -> str:
    return f"${round(value):,}"


class TopStat(QFrame):
    def __init__(self, label: str, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topStat")
        self.setFixedWidth(126)
        self._label = QLabel(label.upper())
        self._label.setObjectName("metricLabel")
        self._value = QLabel("-")
        self._value.setObjectName("metricValue")
        layout = QVBoxLayout()
        layout.setContentsMargins(7, 4, 7, 4)
        layout.setSpacing(0)
        self.setLayout(layout)
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class TimeControlBar(QFrame):
    def __init__(
        self,
        engine: GameEngine,
        theme_manager: ThemeManager,
        parent: QFrame | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._theme_manager = theme_manager
        self.setObjectName("timeBar")
        self.setFixedHeight(52)

        self._date_label = QLabel()
        self._date_label.setObjectName("sectionTitle")
        self._speed_label = QLabel()
        self._speed_label.setObjectName("muted")
        self._tick_label = QLabel()
        self._tick_label.setObjectName("muted")
        self._cash = TopStat("Cash")
        self._revenue_q = TopStat("Revenue/M")
        self._profit_q = TopStat("Profit/M")
        self._debt = TopStat("Debt")
        self._portfolio_value = TopStat("Portfolio")
        self._credit = TopStat("Credit Rating")

        self._theme_selector = QComboBox()
        for theme_name in self._theme_manager.theme_names:
            self._theme_selector.addItem(theme_name)
        self._theme_selector.setCurrentText(self._theme_manager.active_theme.name)
        self._theme_selector.currentTextChanged.connect(self._set_theme)

        pause_button = QPushButton("Pause")
        pause_button.clicked.connect(self._pause)

        step_button = QPushButton("Step")
        step_button.clicked.connect(self._step)

        one_x_button = QPushButton("1x")
        one_x_button.clicked.connect(lambda: self._set_speed(GameSpeed.ONE_X))

        two_x_button = QPushButton("2x")
        two_x_button.clicked.connect(lambda: self._set_speed(GameSpeed.TWO_X))

        five_x_button = QPushButton("5x")
        five_x_button.clicked.connect(lambda: self._set_speed(GameSpeed.FIVE_X))

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        self.setLayout(layout)

        layout.addWidget(self._date_label)
        layout.addWidget(self._speed_label)
        layout.addWidget(self._tick_label)
        layout.addWidget(self._cash)
        layout.addWidget(self._revenue_q)
        layout.addWidget(self._profit_q)
        layout.addWidget(self._debt)
        layout.addWidget(self._portfolio_value)
        layout.addWidget(self._credit)
        layout.addStretch(1)
        layout.addWidget(self._theme_selector)
        layout.addWidget(pause_button)
        layout.addWidget(step_button)
        layout.addWidget(one_x_button)
        layout.addWidget(two_x_button)
        layout.addWidget(five_x_button)

        self.refresh()

    def refresh(self) -> None:
        snapshot = self._engine.snapshot()
        self._date_label.setText(snapshot.current_date.strftime("%B %d, %Y"))
        self._speed_label.setText(snapshot.speed.label)
        self._tick_label.setText(f"Tick {snapshot.tick_count}")
        state = self._engine.state
        companies = self._all_companies(state.player.holding_company.companies)
        debt = sum(company.total_debt for company in companies)
        self._cash.set_value(_money(state.player.holding_company.total_cash()))
        self._revenue_q.set_value(_money(int(state.metadata.get("last_month_revenue", 0))))
        self._profit_q.set_value(_money(int(state.metadata.get("last_month_profit", 0))))
        self._debt.set_value(_money(debt))
        self._portfolio_value.set_value(_money(self._engine.gameplay.company_value(state)))
        self._credit.set_value(str(self._engine.gameplay.credit_rating(state).score))

    def _pause(self) -> None:
        self._engine.pause()
        self.refresh()

    def _step(self) -> None:
        self._engine.step()
        self.refresh()

    def _set_speed(self, speed: GameSpeed) -> None:
        self._engine.set_speed(speed)
        self.refresh()

    def _set_theme(self, theme_name: str) -> None:
        self._theme_manager.set_active_theme(theme_name)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(self._theme_manager.current_stylesheet())

    def _all_companies(self, companies: object) -> list[object]:
        flattened = []
        for company in companies:
            flattened.append(company)
            flattened.extend(self._all_companies(company.subsidiaries))
        return flattened
