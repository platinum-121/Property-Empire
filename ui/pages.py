# ui/pages.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.engine import GameEngine
from industries.real_estate.economy import DealRarity, LandListing, PropertyListing, Zoning
from news.models import NewsItem
from ui.dialogs import NewGameDialog


def _money(value: int | float) -> str:
    prefix = "-" if value < 0 else ""
    return f"{prefix}€{abs(round(value)):,}"


def _money(value: int | float) -> str:
    prefix = "-" if value < 0 else ""
    return f"{prefix}${abs(round(value)):,}"


def _percent(value: int | float) -> str:
    return f"{value * 100:.1f}%"


def _short_money(value: int | float) -> str:
    absolute = abs(round(value))
    prefix = "-" if value < 0 else ""
    if absolute >= 1_000_000_000:
        return f"{prefix}${absolute / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"{prefix}${absolute / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"{prefix}${absolute / 1_000:.1f}K"
    return f"{prefix}${absolute:,}"


def _plain(value: str) -> str:
    return value.replace("_", " ").title()


class Metric(QFrame):
    def __init__(self, label: str, value: str = "-", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metric")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("muted")
        self._value = QLabel(value)
        self._value.setObjectName("metricValue")
        layout.addWidget(label_widget)
        layout.addWidget(self._value)
        self.setLayout(layout)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class SortableItem(QTableWidgetItem):
    def __init__(self, text: str, sort_value: tuple[int, float | str]) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, SortableItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


class DataTable(QTableWidget):
    ROW_HEIGHT = 22
    _instances: list["DataTable"] = []

    MONEY_TOKENS = (
        "cash",
        "cost",
        "rent",
        "profit",
        "debt",
        "value",
        "income",
        "maintenance",
        "price",
        "asking",
        "expense",
        "tax",
        "payment",
        "principal",
        "balance",
        "revenue",
        "fees",
    )

    def __init__(self, headers: tuple[str, ...], parent: QWidget | None = None) -> None:
        super().__init__(0, len(headers), parent)
        self._headers = headers
        self._rows: list[tuple[Any, ...]] = []
        self._keys: list[Any] = []
        self._filter = ""
        self._columns_sized = False
        self.setHorizontalHeaderLabels(headers)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setDefaultSectionSize(110)
        self.horizontalHeader().setMinimumSectionSize(84)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        DataTable._instances.append(self)

    @classmethod
    def set_density(cls, density: str) -> None:
        cls.ROW_HEIGHT = 28 if density == "comfortable" else 22
        active_tables = []
        for table in list(cls._instances):
            try:
                table._apply_rows()
            except RuntimeError:
                continue
            active_tables.append(table)
        cls._instances = active_tables

    def set_rows(self, rows: list[tuple[Any, ...]], row_keys: list[Any] | None = None) -> None:
        self._rows = rows
        self._keys = row_keys or list(range(len(rows)))
        self._apply_rows()

    def set_filter(self, text: str) -> None:
        self._filter = text.strip().lower()
        self._apply_rows()

    def selected_key(self) -> Any:
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _apply_rows(self) -> None:
        selected_key = self.selected_key()
        sort_column = self.horizontalHeader().sortIndicatorSection()
        sort_order = self.horizontalHeader().sortIndicatorOrder()
        self.setSortingEnabled(False)
        visible = [
            (key, row)
            for key, row in zip(self._keys, self._rows, strict=False)
            if not self._filter or self._filter in " ".join(str(value).lower() for value in row)
        ]
        self.setRowCount(len(visible))
        for row_index, (key, row) in enumerate(visible):
            for column_index, value in enumerate(row):
                item = SortableItem(self._display(column_index, value), self._sort_value(value))
                item.setData(Qt.ItemDataRole.UserRole, key)
                if isinstance(value, int | float):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.setItem(row_index, column_index, item)
            self.setRowHeight(row_index, self.ROW_HEIGHT)
        self.setSortingEnabled(True)
        if 0 <= sort_column < self.columnCount():
            self.sortItems(sort_column, sort_order)
        if not self._columns_sized and len(visible) <= 750:
            self.resizeColumnsToContents()
            self._columns_sized = True
        self._enforce_column_widths()
        if selected_key is not None:
            self._restore_selection(selected_key)

    def _enforce_column_widths(self) -> None:
        for column_index, header in enumerate(self._headers):
            header_lower = header.lower()
            minimum = max(92, min(260, len(header) * 9 + 26))
            sample_width = 0
            for row_index in range(min(self.rowCount(), 80)):
                item = self.item(row_index, column_index)
                if item is not None:
                    sample_width = max(sample_width, len(item.text()) * 8 + 28)
            minimum = max(minimum, min(sample_width, 320))
            if any(token in header_lower for token in self.MONEY_TOKENS):
                minimum = max(minimum, 132)
            if any(token in header_lower for token in ("company", "property", "headline", "project", "setting")):
                minimum = max(minimum, 180)
            if any(token in header_lower for token in ("city", "country", "location")):
                minimum = max(minimum, 130)
            if any(token in header_lower for token in ("yield", "occupancy", "growth", "rate", "ltv", "rating")):
                minimum = max(minimum, 112)
            self.setColumnWidth(column_index, max(self.columnWidth(column_index), minimum))

    def _restore_selection(self, key: Any) -> None:
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == key:
                self.selectRow(row)
                return

    def _display(self, column_index: int, value: Any) -> str:
        header = self._headers[min(column_index, len(self._headers) - 1)].lower()
        if isinstance(value, int):
            if any(token in header for token in self.MONEY_TOKENS):
                return _money(value)
            if "m²" in header or "size" in header:
                return f"{value:,}"
            return f"{value:,}"
        if isinstance(value, float):
            if any(token in header for token in ("yield", "occupancy", "growth", "rate", "ltv")):
                return _percent(value)
            return f"{value:,.2f}"
        return str(value)

    def _sort_value(self, value: Any) -> tuple[int, float | str]:
        if isinstance(value, int | float):
            return (0, float(value))
        return (1, str(value).lower())


class Panel(QFrame):
    def __init__(self, title: str, child: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        label = QLabel(title.upper())
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        layout.addWidget(child, stretch=1)
        self.setLayout(layout)


class LineChart(QFrame):
    def __init__(self, title: str, color: str, value_kind: str = "money", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._color = color
        self._value_kind = value_kind
        self._values: list[int] = []
        self.setMinimumHeight(150)

    def set_values(self, values: list[int]) -> None:
        self._values = values[-60:]
        self.update()

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(52, 28, -70, -26)
        painter.setPen(QPen(Qt.GlobalColor.gray, 1))
        painter.drawText(12, 16, self._title)
        if len(self._values) < 2:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No monthly history yet")
            return
        minimum = min(self._values)
        maximum = max(self._values)
        spread = max(maximum - minimum, 1)
        step = rect.width() / (len(self._values) - 1)
        points = []
        for index, value in enumerate(self._values):
            x = rect.left() + index * step
            y = rect.bottom() - ((value - minimum) / spread * rect.height())
            points.append((round(x), round(y)))
        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1))
        painter.drawRect(rect)
        painter.drawText(8, rect.top() + 5, self._format_value(maximum))
        painter.drawText(8, rect.bottom(), self._format_value(minimum))
        painter.drawText(rect.left(), self.height() - 8, "Oldest")
        painter.drawText(rect.right() - 34, self.height() - 8, "Latest")
        painter.setPen(QPen(QColor(self._color), 2))
        for start, end in zip(points, points[1:], strict=False):
            painter.drawLine(start[0], start[1], end[0], end[1])
        painter.setPen(QPen(Qt.GlobalColor.gray, 1))
        painter.drawText(rect.right() + 8, points[-1][1] + 4, self._format_value(self._values[-1]))

    def _format_value(self, value: int | float) -> str:
        if self._value_kind == "percent":
            return f"{value:.1f}%"
        if self._value_kind == "number":
            return f"{round(value):,}"
        absolute = abs(round(value))
        sign = "-" if value < 0 else ""
        if absolute >= 1_000_000_000:
            return f"{sign}${absolute / 1_000_000_000:.1f}B"
        if absolute >= 1_000_000:
            return f"{sign}${absolute / 1_000_000:.1f}M"
        if absolute >= 1_000:
            return f"{sign}${absolute / 1_000:.1f}K"
        return f"{sign}${absolute:,}"


class BasePage(QWidget):
    live_refresh = False

    def __init__(self, engine: GameEngine, title: str, subtitle: str) -> None:
        super().__init__()
        self._engine = engine
        self._root = QVBoxLayout()
        self._root.setContentsMargins(12, 10, 12, 12)
        self._root.setSpacing(8)
        self.setLayout(self._root)

        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("muted")
        self._root.addWidget(title_label)
        self._root.addWidget(subtitle_label)

    def refresh(self) -> None:
        pass

    def run_action(self, action: Callable[[], Any], message: str) -> None:
        try:
            action()
        except ValueError as exc:
            QMessageBox.warning(self, "Action unavailable", str(exc))
            return
        self.refresh()
        QMessageBox.information(self, "Complete", message)


class DashboardPage(BasePage):
    live_refresh = True

    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Dashboard", "Monthly performance, portfolio value, credit health, and recent headlines.")
        self._cash = Metric("Cash")
        self._revenue = Metric("Revenue / Month")
        self._profit = Metric("Profit / Month")
        self._value = Metric("Portfolio Value")
        self._credit = Metric("Credit Rating")
        self._debt = Metric("Debt")
        self._properties = Metric("Properties")
        self._land = Metric("Land")
        metrics = QGridLayout()
        metrics.setSpacing(6)
        for index, metric in enumerate((self._cash, self._revenue, self._profit, self._value, self._credit, self._debt, self._properties, self._land)):
            metrics.addWidget(metric, index // 4, index % 4)
        self._root.addLayout(metrics)

        chart_row = QHBoxLayout()
        self._revenue_chart = LineChart("Revenue / Month", "#5cc8ff")
        self._profit_chart = LineChart("Profit / Month", "#8bd17c")
        self._value_chart = LineChart("Portfolio Value", "#d6b15e")
        chart_row.addWidget(self._revenue_chart)
        chart_row.addWidget(self._profit_chart)
        chart_row.addWidget(self._value_chart)
        self._root.addLayout(chart_row, stretch=1)

        self._news = DataTable(("Date", "Category", "Headline"))
        self._root.addWidget(Panel("Recent News", self._news), stretch=2)

        new_game = QPushButton("New Game")
        new_game.clicked.connect(self._new_game)
        actions = QHBoxLayout()
        actions.addWidget(new_game)
        actions.addStretch(1)
        self._root.addLayout(actions)

    def refresh(self) -> None:
        state = self._engine.state
        gameplay = self._engine.gameplay
        debt = sum(company.total_debt for company in state.player.holding_company.companies)
        history = list(state.metadata.get("operating_history", []))
        self._cash.set_value(_money(state.player.holding_company.total_cash()))
        self._revenue.set_value(_money(int(state.metadata.get("last_month_revenue", 0))))
        self._profit.set_value(_money(int(state.metadata.get("last_month_profit", 0))))
        self._value.set_value(_money(gameplay.company_value(state)))
        self._credit.set_value(str(gameplay.credit_rating(state).score))
        self._debt.set_value(_money(debt))
        self._properties.set_value(str(len(state.player_properties)))
        self._land.set_value(str(len(state.player_land)))
        self._revenue_chart.set_values([int(item["revenue"]) for item in history])
        self._profit_chart.set_values([int(item["profit"]) for item in history])
        self._value_chart.set_values([int(item["company_value"]) for item in history])
        self._news.set_rows([(item.published_on.isoformat(), item.category.value.title(), item.headline) for item in state.news_feed.recent(12)])

    def _new_game(self) -> None:
        dialog = NewGameDialog(self._engine.state.world, self)
        if dialog.exec():
            self._engine.state = self._engine.gameplay.new_game(dialog.company_name, dialog.starting_industry, dialog.hq_city_id)
            self.refresh()


class DealPurchaseDialog(QDialog):
    def __init__(self, engine: GameEngine, listing_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._listing_id = listing_id
        self.setWindowTitle("Inspect Property Deal")
        self.resize(760, 640)
        self._deposit = QLineEdit("25")
        self._term = QLineEdit("120")
        self._offer = QLineEdit()
        self._offer.setPlaceholderText("Offer amount")
        self._details = DataTable(("Metric", "Value"))
        self._cash = DataTable(("Cash Purchase", "Value"))
        self._finance = DataTable(("Finance Purchase", "Value"))
        self._negotiation = DataTable(("Negotiation", "Value"))

        self._deposit.textChanged.connect(self._refresh)
        self._term.textChanged.connect(self._refresh)
        cash_button = QPushButton("Cash Purchase")
        cash_button.clicked.connect(self._cash_purchase)
        finance_button = QPushButton("Finance Purchase")
        finance_button.clicked.connect(self._finance_purchase)
        offer_button = QPushButton("Submit Offer")
        offer_button.clicked.connect(self._submit_offer)
        accept_counter_button = QPushButton("Accept Counteroffer")
        accept_counter_button.clicked.connect(self._accept_counteroffer)
        withdraw_button = QPushButton("Withdraw Offer")
        withdraw_button.clicked.connect(self._withdraw_offer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        finance_controls = QHBoxLayout()
        finance_controls.addWidget(QLabel("Deposit %"))
        finance_controls.addWidget(self._deposit)
        finance_controls.addWidget(QLabel("Loan Months"))
        finance_controls.addWidget(self._term)
        finance_controls.addWidget(QLabel("Offer"))
        finance_controls.addWidget(self._offer)
        finance_controls.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(Panel("Deal Details", self._details), stretch=2)
        layout.addLayout(finance_controls)
        row = QHBoxLayout()
        row.addWidget(Panel("Cash Option", self._cash))
        row.addWidget(Panel("Finance Option", self._finance))
        layout.addLayout(row, stretch=2)
        layout.addWidget(Panel("Negotiation", self._negotiation), stretch=1)
        action_row = QHBoxLayout()
        action_row.addWidget(cash_button)
        action_row.addWidget(finance_button)
        action_row.addWidget(offer_button)
        action_row.addWidget(accept_counter_button)
        action_row.addWidget(withdraw_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self._refresh()

    def _refresh(self) -> None:
        detail = self._engine.gameplay.deal_detail(self._engine.state, self._listing_id)
        self._details.set_rows(
            [
                ("Property Type", detail["property_type"]),
                ("City", detail["city"]),
                ("Country", detail["country"]),
                ("Size", f"{int(detail['size_sqm']):,} m²"),
                ("Zoning / Type", detail["zoning"]),
                ("Asking Price", _money(int(detail["asking_price"]))),
                ("Rent Estimate", f"{_money(int(detail['rent_low']))} - {_money(int(detail['rent_high']))}"),
                ("Rent Per m²", f"€{float(detail['rent_per_sqm']):.2f}"),
                ("Demand Multiplier", f"{float(detail['demand_multiplier']):.2f}x"),
                ("Occupancy Estimate", _percent(float(detail["occupancy"]))),
                ("Revenue / Month", _money(int(detail["rent"]))),
                ("Expenses / Month", _money(int(detail["maintenance"]))),
                ("Profit / Month", _money(int(detail["profit"]))),
                ("Yield", _percent(float(detail["yield"]))),
                ("Rarity", detail["rarity"]),
                ("Days Remaining", str(detail["days_remaining"])),
            ]
        )
        cash_quote = self._engine.gameplay.quote_property_purchase(self._engine.state, self._listing_id, 1.0)
        self._cash.set_rows(
            [
                ("Available Cash", _money(self._engine.state.player.holding_company.total_cash())),
                ("Purchase Price", _money(cash_quote.purchase_price)),
                ("Taxes / Fees", _money(cash_quote.taxes_and_fees)),
                ("Remaining Cash", _money(self._engine.state.player.holding_company.total_cash() - cash_quote.cash_required)),
                ("Affordable", "Yes" if cash_quote.cash_required <= self._engine.state.player.holding_company.total_cash() else "No"),
            ]
        )
        deposit_percent = self._deposit_percent()
        term = self._loan_term()
        finance_quote = self._engine.gameplay.quote_property_purchase(self._engine.state, self._listing_id, deposit_percent, term)
        self._finance.set_rows(
            [
                ("Deposit Amount", _money(finance_quote.deposit_amount)),
                ("Loan Amount", _money(finance_quote.loan_amount)),
                ("Taxes / Fees", _money(finance_quote.taxes_and_fees)),
                ("Interest Rate", _percent(finance_quote.approval.interest_rate)),
                ("Loan Length", f"{finance_quote.approval.term_months} months"),
                ("Monthly Repayment", _money(finance_quote.approval.monthly_repayment)),
                ("Total Interest", _money(max(0, finance_quote.approval.monthly_repayment * finance_quote.approval.term_months - finance_quote.loan_amount))),
                ("Bank Approval", "Approved" if finance_quote.approval.approved else "Rejected"),
                ("Reason", "; ".join(finance_quote.approval.reasons) or finance_quote.approval.reason),
            ]
        )
        negotiation = dict(self._engine.state.metadata.get("negotiations", {})).get(f"property_{self._listing_id}")
        if negotiation:
            self._negotiation.set_rows(
                [
                    ("Status", negotiation["status"]),
                    ("Seller Response", negotiation["seller_response"]),
                    ("Player Offer", _money(int(negotiation["player_offer"]))),
                    ("Counteroffer", _money(int(negotiation["counteroffer"])) if negotiation.get("counteroffer") else "-"),
                    ("Message", negotiation["message"]),
                ]
            )
        else:
            self._negotiation.set_rows([("Status", "No active negotiation")])

    def _cash_purchase(self) -> None:
        try:
            self._engine.gameplay.buy_property_listing(self._engine.state, self._listing_id, 1.0, negotiated_price=self._accepted_offer_price())
        except ValueError as exc:
            QMessageBox.warning(self, "Purchase unavailable", str(exc))
            return
        self.accept()

    def _finance_purchase(self) -> None:
        try:
            self._engine.gameplay.buy_property_listing(self._engine.state, self._listing_id, self._deposit_percent(), self._loan_term(), negotiated_price=self._accepted_offer_price())
        except ValueError as exc:
            QMessageBox.warning(self, "Finance unavailable", str(exc))
            return
        self.accept()

    def _submit_offer(self) -> None:
        try:
            offer = int(self._offer.text().replace("$", "").replace(",", "").strip())
            result = self._engine.gameplay.negotiate_property_offer(self._engine.state, self._listing_id, offer)
        except ValueError as exc:
            QMessageBox.warning(self, "Offer unavailable", str(exc))
            return
        self._refresh()
        QMessageBox.information(self, "Seller response", result.message)

    def _accept_counteroffer(self) -> None:
        try:
            result = self._engine.gameplay.accept_counteroffer(self._engine.state, f"property_{self._listing_id}")
        except ValueError as exc:
            QMessageBox.warning(self, "Counteroffer unavailable", str(exc))
            return
        self._refresh()
        QMessageBox.information(self, "Seller response", result.message)

    def _withdraw_offer(self) -> None:
        try:
            self._engine.gameplay.withdraw_negotiation(self._engine.state, f"property_{self._listing_id}")
        except ValueError as exc:
            QMessageBox.warning(self, "Negotiation unavailable", str(exc))
            return
        self._refresh()

    def _deposit_percent(self) -> float:
        try:
            return max(0.0, min(1.0, float(self._deposit.text()) / 100))
        except ValueError:
            return 0.25

    def _loan_term(self) -> int:
        try:
            return max(12, int(self._term.text()))
        except ValueError:
            return 120

    def _accepted_offer_price(self) -> int | None:
        negotiation = dict(self._engine.state.metadata.get("negotiations", {})).get(f"property_{self._listing_id}")
        if negotiation and negotiation.get("status") == "Accepted":
            return int(negotiation["player_offer"])
        return None


class DealsPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Property Deals", "Review active market deals, filter by location and economics, then buy or finance selected assets.")
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search city, country, type, or zoning")
        self._city = QComboBox()
        self._country = QComboBox()
        self._zoning = QComboBox()
        self._rarity = QComboBox()
        self._min_price = QLineEdit()
        self._min_price.setPlaceholderText("Min price")
        self._max_price = QLineEdit()
        self._max_price.setPlaceholderText("Max price")
        self._min_yield = QLineEdit()
        self._min_yield.setPlaceholderText("Min yield %")
        self._max_size = QLineEdit()
        self._max_size.setPlaceholderText("Max size m²")
        self._sort = QComboBox()
        self._inspect = QPushButton("Inspect / Buy")
        self._inspect.clicked.connect(self._inspect_selected)

        self._country.addItem("All countries", "")
        for country in sorted(self._engine.state.world.countries, key=lambda item: item.name):
            self._country.addItem(country.name, country.country_id)
        self._city.addItem("All cities", "")
        for city in sorted(self._engine.state.world.cities, key=lambda item: item.name):
            self._city.addItem(city.name, city.city_id)
        default_city_id = str(self._engine.state.metadata.get("hq_city_id", "new_york_city"))
        default_index = self._city.findData(default_city_id)
        if default_index >= 0:
            self._city.setCurrentIndex(default_index)
        self._zoning.addItem("All zoning", "")
        for zoning in Zoning:
            self._zoning.addItem(zoning.value, zoning.value)
        self._rarity.addItem("All rarity", "")
        for rarity in DealRarity:
            self._rarity.addItem(rarity.value, rarity.value)
        for label, key in (
            ("Price low to high", "price_low"),
            ("Price high to low", "price_high"),
            ("Size low to high", "size_low"),
            ("Size high to low", "size_high"),
            ("Yield low to high", "yield_low"),
            ("Yield high to low", "yield_high"),
            ("Demand low to high", "demand_low"),
            ("Demand high to low", "demand_high"),
            ("Days remaining", "days_remaining"),
        ):
            self._sort.addItem(label, key)
        self._sort.setCurrentText("Yield high to low")
        for widget in (self._search, self._min_price, self._max_price, self._min_yield, self._max_size):
            widget.textChanged.connect(self.refresh)
        for widget in (self._city, self._country, self._zoning, self._rarity, self._sort):
            widget.currentIndexChanged.connect(self.refresh)

        filters = QGridLayout()
        filters.setSpacing(6)
        controls = (
            ("Search", self._search),
            ("City", self._city),
            ("Country", self._country),
            ("Zoning", self._zoning),
            ("Min Price", self._min_price),
            ("Max Price", self._max_price),
            ("Min Yield", self._min_yield),
            ("Max Size", self._max_size),
            ("Rarity", self._rarity),
            ("Sort", self._sort),
        )
        for index, (label, widget) in enumerate(controls):
            filters.addWidget(QLabel(label), (index // 5) * 2, index % 5)
            filters.addWidget(widget, (index // 5) * 2 + 1, index % 5)
        self._root.addLayout(filters)

        self._table = DataTable(("City", "Country", "Type", "Zoning", "Size m²", "Rent Range", "Rent / m²", "Demand", "Occupancy", "Revenue", "Expenses", "Profit", "Yield", "Asking Price", "Rarity", "Days"))
        self._table.itemDoubleClicked.connect(lambda _: self._inspect_selected())
        self._root.addWidget(self._table, stretch=1)
        actions = QHBoxLayout()
        actions.addWidget(self._inspect)
        actions.addStretch(1)
        self._root.addLayout(actions)

    def refresh(self) -> None:
        listings = self._engine.gameplay.filter_property_deals(
            self._engine.state,
            search=self._search.text(),
            city_id=str(self._city.currentData() or ""),
            country_id=str(self._country.currentData() or ""),
            zoning=str(self._zoning.currentData() or ""),
            min_price=self._money_input(self._min_price),
            max_price=self._money_input(self._max_price),
            min_yield=self._percent_input(self._min_yield),
            max_size_sqm=self._int_input(self._max_size),
            rarity=str(self._rarity.currentData() or ""),
            sort_key=str(self._sort.currentData()),
        )
        rows = []
        keys = []
        for listing in listings:
            context = self._engine.state.world.city_context(listing.city_id)
            if context is None:
                continue
            _, country, _, city = context
            rows.append(
                (
                    city.name,
                    country.name,
                    listing.property_type,
                    listing.zoning.value,
                    listing.size_sqm,
                    f"{_money(listing.estimated_rent_low)} - {_money(listing.estimated_rent_high)}",
                    listing.rent_per_sqm,
                    listing.demand_multiplier,
                    listing.occupancy_rate,
                    listing.monthly_revenue,
                    listing.monthly_expenses,
                    listing.monthly_profit,
                    listing.annual_yield,
                    listing.asking_price,
                    listing.rarity.value,
                    listing.days_remaining,
                )
            )
            keys.append(listing.listing_id)
        self._table.set_rows(rows, keys)

    def _inspect_selected(self) -> None:
        listing_id = self._table.selected_key()
        if listing_id is None:
            QMessageBox.warning(self, "No deal selected", "Select a property deal first.")
            return
        dialog = DealPurchaseDialog(self._engine, str(listing_id), self)
        if dialog.exec():
            self.refresh()

    def _money_input(self, field: QLineEdit) -> int | None:
        text = field.text().replace("$", "").replace("€", "").replace(",", "").strip()
        return int(text) if text else None

    def _int_input(self, field: QLineEdit) -> int | None:
        text = field.text().replace(",", "").strip()
        return int(text) if text else None

    def _percent_input(self, field: QLineEdit) -> float | None:
        text = field.text().replace("%", "").strip()
        return float(text) / 100 if text else None


class PortfolioCityDialog(QDialog):
    def __init__(self, engine: GameEngine, city_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{city_name} Portfolio")
        self.resize(900, 640)
        detail = engine.gameplay.portfolio_city_detail(engine.state, city_name)
        summary = dict(detail["summary"])
        history = list(detail["history"])
        breakdown = list(detail["breakdown"])

        summary_table = DataTable(("Metric", "Value"))
        summary_table.set_rows(
            [
                ("City", summary["city"]),
                ("Country", summary["country"]),
                ("Properties", int(detail["property_count"])),
                ("Average Yield", summary["average_yield"]),
                ("Average Occupancy", summary["average_occupancy"]),
                ("Portfolio Value", summary["portfolio_value"]),
                ("Revenue / Month", summary["revenue_month"]),
                ("Expenses / Month", summary["expenses_month"]),
                ("Profit / Month", summary["profit_month"]),
            ]
        )
        property_table = DataTable(("Property", "Type", "Size m²", "Purchase Price", "Occupancy"))
        property_table.set_rows(breakdown)
        profit_chart = LineChart("City Profit History", "#8bd17c")
        profit_chart.set_values([int(item.get("city_profit", {}).get(city_name, 0)) for item in history])

        layout = QVBoxLayout()
        layout.addWidget(Panel("City Summary", summary_table), stretch=1)
        layout.addWidget(profit_chart, stretch=1)
        layout.addWidget(Panel("Property Breakdown", property_table), stretch=2)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)


class PortfolioPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Portfolio", "City-level portfolio view grouped by property type and monthly performance.")
        self._table = DataTable(("City", "Country", "Houses", "Apartments", "Offices", "Commercial", "Industrial", "Average Yield", "Average Occupancy", "Portfolio Value", "Revenue / Month", "Expenses / Month", "Profit / Month"))
        self._table.itemDoubleClicked.connect(lambda _: self._open_city())
        self._root.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        rows = []
        keys = []
        for group in self._engine.gameplay.portfolio_by_city(self._engine.state):
            rows.append(
                (
                    group["city"],
                    group["country"],
                    group["Houses"],
                    group["Apartments"],
                    group["Offices"],
                    group["Commercial"],
                    group["Industrial"],
                    group["average_yield"],
                    group["average_occupancy"],
                    group["portfolio_value"],
                    group["revenue_month"],
                    group["expenses_month"],
                    group["profit_month"],
                )
            )
            keys.append(group["city"])
        self._table.set_rows(rows, keys)

    def _open_city(self) -> None:
        city_name = self._table.selected_key()
        if city_name is None:
            return
        PortfolioCityDialog(self._engine, str(city_name), self).exec()


class CityManagersPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "City Managers", "Late-game automation for routine small property purchases.")
        self._city = QComboBox()
        self._name = QLineEdit("City Manager")
        self._budget = QLineEdit("5000000")
        self._min_yield = QLineEdit("7")
        self._max_price = QLineEdit("2500000")
        self._reserve = QLineEdit("20000000")
        self._aggressiveness = QComboBox()
        for label in ("Conservative", "Balanced", "Aggressive"):
            self._aggressiveness.addItem(label, label)
        self._types = {
            Zoning.RESIDENTIAL.value: QCheckBox("Residential"),
            Zoning.OFFICE.value: QCheckBox("Office"),
            Zoning.COMMERCIAL.value: QCheckBox("Commercial"),
            Zoning.INDUSTRIAL.value: QCheckBox("Industrial"),
        }
        for checkbox in self._types.values():
            checkbox.setChecked(True)
        assign = QPushButton("Assign Manager")
        assign.clicked.connect(self._assign)
        update = QPushButton("Update Settings")
        update.clicked.connect(self._update)
        remove = QPushButton("Remove Manager")
        remove.clicked.connect(self._remove)
        self._table = DataTable(("Manager", "City", "Monthly Budget", "Minimum Yield", "Max Price", "Types", "Aggressiveness", "Cash Reserve", "Purchased", "Invested", "Average Yield", "Status"))

        form = QGridLayout()
        controls = (
            ("City", self._city),
            ("Name", self._name),
            ("Monthly Budget", self._budget),
            ("Minimum Yield %", self._min_yield),
            ("Max Property Price", self._max_price),
            ("Cash Reserve", self._reserve),
            ("Aggressiveness", self._aggressiveness),
        )
        for index, (label, widget) in enumerate(controls):
            form.addWidget(QLabel(label), (index // 4) * 2, index % 4)
            form.addWidget(widget, (index // 4) * 2 + 1, index % 4)
        type_row = QHBoxLayout()
        for checkbox in self._types.values():
            type_row.addWidget(checkbox)
        action_row = QHBoxLayout()
        action_row.addWidget(assign)
        action_row.addWidget(update)
        action_row.addWidget(remove)
        action_row.addStretch(1)
        self._root.addLayout(form)
        self._root.addLayout(type_row)
        self._root.addLayout(action_row)
        self._root.addWidget(Panel("Managers", self._table), stretch=1)

    def refresh(self) -> None:
        current_city = self._city.currentData()
        self._city.clear()
        operated = sorted({property_.city_id for property_ in self._engine.state.player_properties})
        for city_id in operated:
            city = self._engine.state.world.get_city(city_id)
            if city is not None:
                self._city.addItem(city.name, city.city_id)
        if current_city is not None:
            index = self._city.findData(current_city)
            if index >= 0:
                self._city.setCurrentIndex(index)
        if not self._engine.gameplay.city_manager_unlocked(self._engine.state):
            self._table.set_rows([("Locked", "Research Property Management Division", 0, 0.0, 0, "-", "-", 0, 0, 0, 0.0, "Locked")])
            return
        rows = []
        keys = []
        for manager in self._engine.gameplay.city_manager_rows(self._engine.state):
            rows.append(
                (
                    manager["name"],
                    manager["city"],
                    manager["monthly_budget"],
                    manager["min_yield"],
                    manager["max_property_price"],
                    manager["allowed_property_types"],
                    manager["aggressiveness"],
                    manager["cash_reserve_requirement"],
                    manager["properties_purchased"],
                    manager["capital_invested"],
                    manager["average_yield"],
                    manager["status"],
                )
            )
            keys.append(manager["city_id"])
        self._table.set_rows(rows, keys)

    def _allowed_types(self) -> tuple[str, ...]:
        return tuple(zoning for zoning, checkbox in self._types.items() if checkbox.isChecked())

    def _manager_inputs(self) -> tuple[int, float, int, tuple[str, ...], str, int]:
        return (
            int(self._budget.text().replace("$", "").replace(",", "").strip()),
            float(self._min_yield.text().replace("%", "").strip()) / 100,
            int(self._max_price.text().replace("$", "").replace(",", "").strip()),
            self._allowed_types(),
            str(self._aggressiveness.currentData()),
            int(self._reserve.text().replace("$", "").replace(",", "").strip()),
        )

    def _assign(self) -> None:
        city_id = str(self._city.currentData() or "")
        budget, min_yield, max_price, allowed, aggressiveness, reserve = self._manager_inputs()
        self.run_action(lambda: self._engine.gameplay.assign_city_manager(self._engine.state, city_id, self._name.text(), budget, min_yield, max_price, allowed, aggressiveness, reserve), "City manager assigned.")

    def _update(self) -> None:
        city_id = str(self._table.selected_key() or self._city.currentData() or "")
        budget, min_yield, max_price, allowed, aggressiveness, reserve = self._manager_inputs()
        self.run_action(lambda: self._engine.gameplay.update_city_manager(self._engine.state, city_id, budget, min_yield, max_price, allowed, aggressiveness, reserve), "City manager updated.")

    def _remove(self) -> None:
        city_id = str(self._table.selected_key() or self._city.currentData() or "")
        self.run_action(lambda: self._engine.gameplay.remove_city_manager(self._engine.state, city_id), "City manager removed.")


class LandDevelopmentPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Land & Development", "Buy development sites and start construction based on zoning.")
        self._city = QComboBox()
        for city in sorted(self._engine.state.world.cities, key=lambda item: item.name):
            self._city.addItem(city.name, city.city_id)
        self._city.setCurrentText("New York City")
        self._city.currentIndexChanged.connect(self.refresh)
        buy_land = QPushButton("Buy Selected Land")
        buy_land.clicked.connect(self._buy_land)
        start = QPushButton("Start Development")
        start.clicked.connect(self._start_development)
        proceed_mega = QPushButton("Proceed Mega Project")
        proceed_mega.clicked.connect(self._proceed_mega)
        delay_mega = QPushButton("Delay Mega Project")
        delay_mega.clicked.connect(self._delay_mega)
        reject_mega = QPushButton("Reject Mega Project")
        reject_mega.clicked.connect(self._reject_mega)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("City"))
        controls.addWidget(self._city)
        controls.addWidget(buy_land)
        controls.addWidget(start)
        controls.addStretch(1)
        self._root.addLayout(controls)
        self._land_market = DataTable(("City", "Country", "Size m²", "Zoning", "Demand", "Asking Price", "Days"))
        self._owned_land = DataTable(("Parcel", "City", "Size m²", "Zoning", "Demand", "Purchase Price", "Developed"))
        self._owned_land.itemSelectionChanged.connect(self._refresh_options)
        self._options = DataTable(("Option", "Zoning", "Construction Cost", "Build Time", "Unit Count", "Expected Rent", "Maintenance", "Yield", "Planning"))
        self._mega = DataTable(("Project", "Location", "Type", "Cost", "Duration", "Revenue", "Profit", "Risk", "Prestige", "Status", "Days"))
        row = QHBoxLayout()
        row.addWidget(Panel("Land Marketplace", self._land_market))
        row.addWidget(Panel("Owned Land", self._owned_land))
        self._root.addLayout(row, stretch=1)
        self._root.addWidget(Panel("Development Options", self._options), stretch=1)
        mega_actions = QHBoxLayout()
        mega_actions.addWidget(proceed_mega)
        mega_actions.addWidget(delay_mega)
        mega_actions.addWidget(reject_mega)
        mega_actions.addStretch(1)
        self._root.addLayout(mega_actions)
        self._root.addWidget(Panel("Mega Projects", self._mega), stretch=1)

    def refresh(self) -> None:
        city_id = str(self._city.currentData())
        rows = []
        keys = []
        for listing in self._engine.gameplay.land_listings(self._engine.state, city_id):
            context = self._engine.state.world.city_context(listing.city_id)
            if context is None:
                continue
            _, country, _, city = context
            rows.append((city.name, country.name, listing.size_sqm, listing.zoning.value, listing.demand_multiplier, listing.asking_price, listing.days_remaining))
            keys.append(listing.listing_id)
        self._land_market.set_rows(rows, keys)
        self._owned_land.set_rows(
            [
                (parcel.name, self._engine.gameplay._city_name(self._engine.state, parcel.city_id), parcel.size_sqm, parcel.zoning.value, parcel.demand_multiplier, parcel.purchase_price, "Yes" if parcel.developed else "No")
                for parcel in self._engine.state.player_land
            ],
            [parcel.parcel_id for parcel in self._engine.state.player_land],
        )
        self._refresh_options()
        mega_rows = self._engine.gameplay.mega_project_rows(self._engine.state)
        self._mega.set_rows(
            [
                (
                    row["name"],
                    row["location"],
                    row["project_type"],
                    row["estimated_cost"],
                    row["construction_days"],
                    row["expected_revenue"],
                    row["expected_profit"],
                    row["risk_rating"],
                    row["prestige_reward"],
                    row["status"],
                    row["days_remaining"],
                )
                for row in mega_rows
            ],
            [row["project_id"] for row in mega_rows],
        )

    def _refresh_options(self) -> None:
        parcel_id = self._owned_land.selected_key()
        rows = []
        keys = []
        parcels = {parcel.parcel_id: parcel for parcel in self._engine.state.player_land}
        parcel = parcels.get(parcel_id)
        if parcel is None:
            self._options.set_rows([], [])
            return
        company_id = self._engine.gameplay.construction_companies()[1].company_id
        for option in self._engine.gameplay.development_options(parcel.zoning):
            quote = self._engine.gameplay.development_quote(self._engine.state, parcel.parcel_id, option.option_id, company_id)
            rows.append((option.name, option.zoning.value, quote["construction_cost"], quote["build_time_days"], quote["unit_count"], quote["expected_rent"], quote["expected_maintenance"], quote["expected_yield"], "Yes" if quote["planning_required"] else "No"))
            keys.append(option.option_id)
        self._options.set_rows(rows, keys)

    def _buy_land(self) -> None:
        listing_id = self._land_market.selected_key()
        if listing_id is None:
            QMessageBox.warning(self, "No land selected", "Select a land plot first.")
            return
        self.run_action(lambda: self._engine.gameplay.buy_land_listing(self._engine.state, str(listing_id)), "Land purchased.")

    def _start_development(self) -> None:
        parcel_id = self._owned_land.selected_key()
        option_id = self._options.selected_key()
        if parcel_id is None or option_id is None:
            QMessageBox.warning(self, "Selection needed", "Select owned land and a development option.")
            return
        company_id = self._engine.gameplay.construction_companies()[1].company_id
        self.run_action(lambda: self._engine.gameplay.start_development(self._engine.state, str(parcel_id), str(option_id), company_id), "Construction started.")

    def _selected_mega(self) -> str:
        project_id = self._mega.selected_key()
        if project_id is None:
            raise ValueError("Select a mega project first.")
        return str(project_id)

    def _proceed_mega(self) -> None:
        self.run_action(lambda: self._engine.gameplay.proceed_mega_project(self._engine.state, self._selected_mega()), "Mega project started.")

    def _delay_mega(self) -> None:
        self.run_action(lambda: self._engine.gameplay.delay_mega_project(self._engine.state, self._selected_mega()), "Mega project delayed.")

    def _reject_mega(self) -> None:
        self.run_action(lambda: self._engine.gameplay.reject_mega_project(self._engine.state, self._selected_mega()), "Mega project rejected.")


class FinancialsPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Finance & Tax", "Statements, cash flow, tax position, rates, and filing forecast.")
        self._cash = Metric("Cash")
        self._assets = Metric("Managed Assets")
        self._debt = Metric("Debt")
        self._net_profit = Metric("Net Profit")
        self._taxable_profit = Metric("Taxable Profit")
        self._tax_paid = Metric("Tax Paid")
        metric_row = QGridLayout()
        for index, metric in enumerate((self._cash, self._assets, self._debt, self._net_profit, self._taxable_profit, self._tax_paid)):
            metric_row.addWidget(metric, index // 3, index % 3)
        self._root.addLayout(metric_row)

        chart_row = QHBoxLayout()
        self._cash_chart = LineChart("Cash", "#d6b15e")
        self._profit_chart = LineChart("Profit / Month", "#8bd17c")
        self._debt_chart = LineChart("Debt", "#c75f5f")
        self._tax_chart = LineChart("Tax Paid", "#b8876b")
        for chart in (self._cash_chart, self._profit_chart, self._debt_chart, self._tax_chart):
            chart_row.addWidget(chart)
        self._root.addLayout(chart_row, stretch=1)

        self._income = DataTable(("Section", "Line", "Amount"))
        self._balance = DataTable(("Section", "Line", "Amount"))
        self._cashflow = DataTable(("Section", "Line", "Amount"))
        self._tax_summary = DataTable(("Tax Summary", "Amount"))
        self._tax_rates = DataTable(("Rate / Filing", "Value"))
        self._tax_history = DataTable(("Month", "Tax Paid", "Revenue", "Profit"))
        row = QHBoxLayout()
        row.addWidget(Panel("Income Statement", self._income))
        row.addWidget(Panel("Balance Sheet", self._balance))
        row.addWidget(Panel("Cash Flow", self._cashflow))
        self._root.addLayout(row, stretch=1)
        tax_row = QHBoxLayout()
        tax_row.addWidget(Panel("Tax Summary", self._tax_summary))
        tax_row.addWidget(Panel("Tax Rates & Forecast", self._tax_rates))
        tax_row.addWidget(Panel("Monthly Tax History", self._tax_history))
        self._root.addLayout(tax_row, stretch=1)

    def refresh(self) -> None:
        gameplay = self._engine.gameplay
        state = self._engine.state
        tax_detail = gameplay.tax_detail(state)
        tax_summary = dict(tax_detail["summary"])
        total_tax_paid = int(tax_summary.get("Corporate tax paid", 0)) + int(tax_summary.get("Property tax paid", 0)) + int(tax_summary.get("Stamp duty paid", 0))
        total_debt = sum(int(row[3]) for row in gameplay.loan_centre_rows(state))
        self._cash.set_value(_money(state.player.holding_company.total_cash()))
        self._assets.set_value(_money(gameplay.company_value(state)))
        self._debt.set_value(_money(total_debt))
        self._net_profit.set_value(_money(state.financials.income_statement.profit))
        self._taxable_profit.set_value(_money(int(tax_summary.get("Taxable profit", 0))))
        self._tax_paid.set_value(_money(total_tax_paid))
        history = list(state.metadata.get("operating_history", []))
        self._cash_chart.set_values([int(item.get("cash", 0)) for item in history])
        self._profit_chart.set_values([int(item.get("profit", 0)) for item in history])
        self._debt_chart.set_values([int(item.get("debt", 0)) for item in history])
        self._tax_chart.set_values([int(item.get("tax_paid", 0)) for item in history])
        self._income.set_rows(gameplay.income_statement_lines(state))
        self._balance.set_rows(gameplay.balance_sheet_lines(state))
        self._cashflow.set_rows(gameplay.cash_flow_lines(state))
        self._tax_summary.set_rows(tax_detail["summary"])
        self._tax_rates.set_rows(tax_detail["rates"] + tax_detail["forecast"])
        self._tax_history.set_rows(tax_detail["monthly_history"])


class LoanCentrePage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Loans", "Loan overview and repayment controls.")
        self._repayment = QLineEdit("100000")
        partial = QPushButton("Partial Repayment")
        partial.clicked.connect(self._partial)
        full = QPushButton("Full Repayment")
        full.clicked.connect(self._full)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Repayment"))
        controls.addWidget(self._repayment)
        controls.addWidget(partial)
        controls.addWidget(full)
        controls.addStretch(1)
        self._root.addLayout(controls)
        self._table = DataTable(("Loan", "Name", "Original Principal", "Remaining Balance", "Interest Rate", "Term Remaining", "Monthly Payment", "Secured Property / Deal", "Status"))
        self._root.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        rows = self._engine.gameplay.loan_centre_rows(self._engine.state)
        self._table.set_rows(rows, [row[0] for row in rows])

    def _partial(self) -> None:
        loan_id = self._selected()
        amount = int(self._repayment.text().replace("$", "").replace(",", "").strip())
        self.run_action(lambda: self._engine.gameplay.repay_company_loan(self._engine.state, loan_id, amount), "Loan repayment complete.")

    def _full(self) -> None:
        loan_id = self._selected()
        rows = {row[0]: row for row in self._engine.gameplay.loan_centre_rows(self._engine.state)}
        amount = int(rows[loan_id][3])
        self.run_action(lambda: self._engine.gameplay.repay_company_loan(self._engine.state, loan_id, amount), "Loan fully repaid.")

    def _selected(self) -> str:
        key = self._table.selected_key()
        if key is None:
            raise ValueError("Select a loan first.")
        return str(key)


class TaxPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Tax", "Tax position, rates, forecasts, and monthly history.")
        self._summary = DataTable(("Summary", "Amount"))
        self._rates = DataTable(("Rate", "Value"))
        self._forecast = DataTable(("Forecast / Filing", "Value"))
        self._history = DataTable(("Month", "Tax Paid", "Revenue", "Profit"))
        top = QHBoxLayout()
        top.addWidget(Panel("Tax Summary", self._summary))
        top.addWidget(Panel("Rates", self._rates))
        top.addWidget(Panel("Forecast", self._forecast))
        self._root.addLayout(top, stretch=1)
        self._root.addWidget(Panel("Monthly Tax History", self._history), stretch=2)

    def refresh(self) -> None:
        detail = self._engine.gameplay.tax_detail(self._engine.state)
        self._summary.set_rows(detail["summary"])
        self._rates.set_rows(detail["rates"])
        self._forecast.set_rows(detail["forecast"])
        self._history.set_rows(detail["monthly_history"])


class CitiesPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Cities", "Market demand, growth, competition, and access status.")
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search city or country")
        self._search.textChanged.connect(lambda text: self._table.set_filter(text))
        self._table = DataTable(("City", "Country", "Population", "Growth", "Demand", "Average Yield", "Competition", "Access Status"))
        self._root.addWidget(self._search)
        self._root.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        rows = []
        for row in self._engine.gameplay.city_market_rows(self._engine.state):
            rows.append((row["city"], row["country"], row["population"], row["growth"], row["demand"], row["average_yield"], row["competition"], row["access_status"]))
        self._table.set_rows(rows)


class CreditRatingPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Credit & Loans", "Credit score factors, borrowing capacity, loan book, and repayment controls.")
        self._score = Metric("Current Rating")
        self._band = Metric("Rating Band")
        self._capacity = Metric("Borrowing Capacity")
        self._rate = Metric("Interest Estimate")
        self._debt = Metric("Total Debt")
        self._leverage = Metric("Leverage")
        metrics = QHBoxLayout()
        for metric in (self._score, self._band, self._capacity, self._rate, self._debt, self._leverage):
            metrics.addWidget(metric)
        self._root.addLayout(metrics)

        self._repayment = QLineEdit("100000")
        partial = QPushButton("Partial Repayment")
        partial.clicked.connect(self._partial)
        full = QPushButton("Full Repayment")
        full.clicked.connect(self._full)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Repayment"))
        controls.addWidget(self._repayment)
        controls.addWidget(partial)
        controls.addWidget(full)
        controls.addStretch(1)
        self._root.addLayout(controls)

        self._factors = DataTable(("Factor", "Impact", "Status", "Detail"))
        self._loans = DataTable(("Loan", "Name", "Original Principal", "Remaining Balance", "Interest Rate", "Term Remaining", "Monthly Payment", "Secured Property / Deal", "Status"))
        self._positive = DataTable(("Positive Factors",))
        self._negative = DataTable(("Negative Factors",))
        row = QHBoxLayout()
        row.addWidget(Panel("Credit Factors", self._factors))
        row.addWidget(Panel("Loan Book", self._loans))
        self._root.addLayout(row, stretch=2)
        bottom = QHBoxLayout()
        bottom.addWidget(Panel("Positive Factors", self._positive))
        bottom.addWidget(Panel("Negative Factors", self._negative))
        self._root.addLayout(bottom, stretch=1)

    def refresh(self) -> None:
        profile = self._engine.gameplay.credit_profile(self._engine.state)
        debt = sum(company.total_debt for company in self._engine.state.player.holding_company.companies)
        value = max(self._engine.gameplay.company_value(self._engine.state), 1)
        self._score.set_value(str(profile["score"]))
        self._band.set_value(str(profile["band"]))
        self._capacity.set_value(_money(int(profile["borrowing_capacity"])))
        self._rate.set_value(_percent(float(profile["interest_rate_estimate"])))
        self._debt.set_value(_money(debt))
        self._leverage.set_value(_percent(debt / value))
        self._factors.set_rows(
            [
                (factor["factor"], int(factor["impact"]), factor["status"], factor["detail"])
                for factor in profile["factors"]
            ]
        )
        loan_rows = self._engine.gameplay.loan_centre_rows(self._engine.state)
        self._loans.set_rows(loan_rows, [row[0] for row in loan_rows])
        self._positive.set_rows([(factor,) for factor in profile["positive_factors"]])
        self._negative.set_rows([(factor,) for factor in profile["negative_factors"]])

    def _partial(self) -> None:
        loan_id = self._selected()
        amount = int(self._repayment.text().replace("$", "").replace(",", "").strip())
        self.run_action(lambda: self._engine.gameplay.repay_company_loan(self._engine.state, loan_id, amount), "Loan repayment complete.")

    def _full(self) -> None:
        loan_id = self._selected()
        rows = {row[0]: row for row in self._engine.gameplay.loan_centre_rows(self._engine.state)}
        amount = int(rows[loan_id][3])
        self.run_action(lambda: self._engine.gameplay.repay_company_loan(self._engine.state, loan_id, amount), "Loan fully repaid.")

    def _selected(self) -> str:
        key = self._loans.selected_key()
        if key is None:
            raise ValueError("Select a loan first.")
        return str(key)


class ReportsPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Reports", "Monthly reports, quarterly summaries, and operating history.")
        self._charts = {
            "cash": LineChart("Cash History", "#d6b15e"),
            "debt": LineChart("Debt History", "#c75f5f"),
            "portfolio_value": LineChart("Portfolio Value", "#78a6c8"),
            "credit_rating": LineChart("Credit Rating", "#8bd17c", "number"),
            "occupancy": LineChart("Occupancy", "#5cc8ff", "percent"),
            "yield": LineChart("Yield", "#d6a84f", "percent"),
            "tax_paid": LineChart("Tax Paid", "#b8876b"),
            "construction_pipeline": LineChart("Construction Pipeline", "#a48ad4"),
        }
        self._reports = DataTable(("Date", "Type", "Metric", "Value"))
        self._alerts = DataTable(("Date", "Category", "Alert", "Message"))
        chart_grid = QGridLayout()
        for index, chart in enumerate(self._charts.values()):
            chart_grid.addWidget(chart, index // 4, index % 4)
        self._root.addLayout(chart_grid, stretch=2)
        row = QHBoxLayout()
        row.addWidget(Panel("Reports", self._reports))
        row.addWidget(Panel("Alerts", self._alerts))
        self._root.addLayout(row, stretch=2)

    def refresh(self) -> None:
        history = list(self._engine.state.metadata.get("operating_history", []))
        for key, chart in self._charts.items():
            scale = 100 if key in {"occupancy", "yield"} else 1
            chart.set_values([round(float(item.get(key, 0)) * scale) for item in history])
        rows = []
        for report in self._engine.state.metadata.get("reports", [])[-20:]:
            summary = dict(report.get("summary", {}))
            for metric, value in summary.items():
                rows.append((report.get("date", ""), str(report.get("type", "")).title(), metric, value))
        self._reports.set_rows(rows)
        self._alerts.set_rows(
            [
                (alert["date"], alert["category"], alert["title"], alert["message"])
                for alert in self._engine.gameplay.alerts(self._engine.state)
            ]
        )


class ResearchPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Research", "Tiered property research tree with long-term billion-dollar unlocks.")
        self._selected: str | None = None
        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(("Research Tree", "Status", "Cost", "Effect"))
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self._tree.itemSelectionChanged.connect(self._select_from_tree)
        self._tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._tree.header().setStretchLastSection(True)
        self._detail = DataTable(("Research", "Value"))
        self._fund_button = QPushButton("Fund Selected Research")
        self._fund_button.setObjectName("primaryButton")
        self._fund_button.setEnabled(False)
        self._fund_button.clicked.connect(self._fund)
        row = QHBoxLayout()
        row.addWidget(Panel("Research Tree", self._tree), stretch=3)
        row.addWidget(Panel("Selected Unlock", self._detail), stretch=2)
        self._root.addLayout(row, stretch=1)
        self._root.addWidget(self._fund_button)

    def refresh(self) -> None:
        selected = self._selected
        self._tree.clear()
        nodes = self._engine.gameplay.research_tree(self._engine.state)
        categories = ("Property Management", "Development", "Finance", "Planning", "Corporate")
        by_id = {str(node["node_id"]): node for node in nodes}
        children: dict[str, list[dict[str, Any]]] = {str(node["node_id"]): [] for node in nodes}
        roots: dict[str, list[dict[str, Any]]] = {category: [] for category in categories}
        for node in nodes:
            prerequisites = tuple(str(item) for item in node["prerequisites"])
            if prerequisites and prerequisites[0] in children:
                children[prerequisites[0]].append(node)
            else:
                roots.setdefault(str(node["category"]), []).append(node)

        for category in categories:
            category_item = QTreeWidgetItem((category, "", "", ""))
            category_item.setExpanded(True)
            self._tree.addTopLevelItem(category_item)
            for node in roots.get(category, []):
                self._add_research_item(category_item, node, children)

        self._tree.resizeColumnToContents(0)
        if selected and selected in by_id:
            self._select_tree_item(selected)
            self._select(selected)
        else:
            self._detail.set_rows([("Selection", "Choose a research unlock from the tree.")])
            self._fund_button.setEnabled(False)

    def _add_research_item(
        self,
        parent: QTreeWidgetItem,
        node: dict[str, Any],
        children: dict[str, list[dict[str, Any]]],
    ) -> None:
        item = QTreeWidgetItem(
            (
                str(node["name"]),
                str(node["status"]),
                _short_money(int(node["cost"])),
                str(node["effect_summary"]),
            )
        )
        item.setData(0, Qt.ItemDataRole.UserRole, str(node["node_id"]))
        status = str(node["status"])
        if status == "Completed":
            item.setForeground(1, QBrush(QColor("#8bd17c")))
        elif status == "Available":
            item.setForeground(1, QBrush(QColor("#d6b15e")))
        elif status == "Locked":
            item.setForeground(1, QBrush(QColor("#8a949e")))
        parent.addChild(item)
        if status in {"Available", "Completed"}:
            item.setExpanded(True)
        for child in children.get(str(node["node_id"]), []):
            self._add_research_item(item, child, children)

    def _select_tree_item(self, node_id: str) -> None:
        matches = self._tree.findItems("*", Qt.MatchFlag.MatchWildcard | Qt.MatchFlag.MatchRecursive, 0)
        for item in matches:
            if item.data(0, Qt.ItemDataRole.UserRole) == node_id:
                self._tree.setCurrentItem(item)
                return

    def _select_from_tree(self) -> None:
        item = self._tree.currentItem()
        node_id = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if node_id is None:
            self._selected = None
            self._fund_button.setEnabled(False)
            return
        self._select(str(node_id))

    def _select(self, node_id: str) -> None:
        self._selected = node_id
        node = next(item for item in self._engine.gameplay.research_tree(self._engine.state) if item["node_id"] == node_id)
        available_cash = self._engine.state.player.holding_company.total_cash()
        status = str(node["status"])
        readiness = "Ready to fund" if status == "Available" and available_cash >= int(node["cost"]) else "Needs more cash" if status == "Available" else status
        self._fund_button.setEnabled(status == "Available")
        self._detail.set_rows(
            [
                ("Name", node["name"]),
                ("Category", node["category"]),
                ("Status", status),
                ("Cost", node["cost"]),
                ("Available Cash", available_cash),
                ("Funding Readiness", readiness),
                ("Unlock", node["description"]),
                ("Exact Effects", "; ".join(str(effect) for effect in node["effects"])),
                ("Prerequisites", ", ".join(node["prerequisites"]) or "None"),
                ("Tree Tier", self._research_levels(self._engine.gameplay.research_tree(self._engine.state))[node_id] + 1),
            ]
        )

    def _fund(self) -> None:
        if self._selected is None:
            QMessageBox.warning(self, "No research selected", "Select a research node first.")
            return
        self.run_action(lambda: self._engine.gameplay.start_research(self._engine.state, self._selected or ""), "Research completed.")

    def _research_levels(self, nodes: list[dict[str, Any]]) -> dict[str, int]:
        by_id = {str(node["node_id"]): node for node in nodes}
        cache: dict[str, int] = {}

        def level_for(node_id: str) -> int:
            if node_id in cache:
                return cache[node_id]
            prerequisites = tuple(str(item) for item in by_id[node_id]["prerequisites"])
            cache[node_id] = 0 if not prerequisites else 1 + max(level_for(prerequisite) for prerequisite in prerequisites)
            return cache[node_id]

        return {node_id: level_for(node_id) for node_id in by_id}


class CompetitorsPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Competitors", "Property competitors and whole-portfolio acquisition opportunities.")
        self._table = DataTable(("Company", "Cash", "Debt", "Reputation", "Offices", "Portfolio Value", "Traits"))
        self._acquisitions = DataTable(("Company", "Portfolio Value", "Debt", "Cities", "Property Count", "Revenue", "Profit", "Asking Price"))
        buy = QPushButton("Buy Selected Portfolio")
        buy.clicked.connect(self._buy_portfolio)
        row = QHBoxLayout()
        row.addWidget(Panel("Competitors", self._table))
        row.addWidget(Panel("Portfolio Acquisitions", self._acquisitions))
        self._root.addLayout(row, stretch=1)
        self._root.addWidget(buy)

    def refresh(self) -> None:
        rows = []
        for company in self._engine.state.npc_companies:
            rows.append((company.name, company.cash, company.total_debt, company.reputation, company.branch_count, sum(asset.value for asset in company.assets), ", ".join(_plain(trait.value) for trait in company.npc_traits) or "Standard"))
        self._table.set_rows(rows)
        acquisition_rows = []
        keys = []
        for opportunity in self._engine.gameplay.portfolio_acquisition_opportunities(self._engine.state):
            acquisition_rows.append(
                (
                    opportunity.company_name,
                    opportunity.portfolio_value,
                    opportunity.debt,
                    ", ".join(opportunity.cities),
                    opportunity.property_count,
                    opportunity.revenue_month,
                    opportunity.profit_month,
                    opportunity.asking_price,
                )
            )
            keys.append(opportunity.company_id)
        self._acquisitions.set_rows(acquisition_rows, keys)

    def _buy_portfolio(self) -> None:
        company_id = self._acquisitions.selected_key()
        if company_id is None:
            QMessageBox.warning(self, "No portfolio selected", "Select a portfolio acquisition first.")
            return
        self.run_action(lambda: self._engine.gameplay.buy_competitor_portfolio(self._engine.state, str(company_id)), "Competitor portfolio acquired.")


class SettingsPage(BasePage):
    def __init__(self, engine: GameEngine) -> None:
        super().__init__(engine, "Settings", "Gameplay and interface preferences for this save.")
        self._report_popups = QComboBox()
        self._report_popups.addItem("Enabled", True)
        self._report_popups.addItem("Disabled", False)
        self._table_density = QComboBox()
        self._table_density.addItem("Compact", "compact")
        self._table_density.addItem("Comfortable", "comfortable")
        self._developer_money = QComboBox()
        self._developer_money.addItem("Enabled", True)
        self._developer_money.addItem("Disabled", False)
        apply_button = QPushButton("Apply Settings")
        apply_button.clicked.connect(self._apply)

        form = QGridLayout()
        form.addWidget(QLabel("Report popups"), 0, 0)
        form.addWidget(self._report_popups, 0, 1)
        form.addWidget(QLabel("Table density"), 1, 0)
        form.addWidget(self._table_density, 1, 1)
        form.addWidget(QLabel("Developer money menu"), 2, 0)
        form.addWidget(self._developer_money, 2, 1)
        form.addWidget(QLabel("Shortcut"), 3, 0)
        form.addWidget(QLabel("Ctrl+M"), 3, 1)
        self._settings = DataTable(("Setting", "Value"))
        self._root.addLayout(form)
        self._root.addWidget(apply_button)
        self._root.addWidget(Panel("Current Save Settings", self._settings), stretch=1)

    def refresh(self) -> None:
        metadata = self._engine.state.metadata
        report_popups = bool(metadata.get("setting_show_report_popups", True))
        table_density = str(metadata.get("setting_table_density", "compact"))
        developer_money = bool(metadata.get("setting_developer_money_enabled", True))
        DataTable.set_density(table_density)
        self._report_popups.setCurrentText("Enabled" if report_popups else "Disabled")
        self._table_density.setCurrentText(table_density.title())
        self._developer_money.setCurrentText("Enabled" if developer_money else "Disabled")
        self._settings.set_rows(
            [
                ("Report popups", "Enabled" if report_popups else "Disabled"),
                ("Table density", str(metadata.get("setting_table_density", "compact")).title()),
                ("Ctrl+M developer money", "Enabled" if developer_money else "Disabled"),
                ("Reports pause simulation", "No"),
            ]
        )

    def _apply(self) -> None:
        metadata = self._engine.state.metadata
        metadata["setting_show_report_popups"] = bool(self._report_popups.currentData())
        metadata["setting_table_density"] = str(self._table_density.currentData())
        metadata["setting_developer_money_enabled"] = bool(self._developer_money.currentData())
        DataTable.set_density(str(metadata["setting_table_density"]))
        self.refresh()
        QMessageBox.information(self, "Settings saved", "Settings updated for this save.")


class PlaceholderPage(BasePage):
    def __init__(self, engine: GameEngine, title: str) -> None:
        super().__init__(engine, title, "Locked for this phase.")
        label = QLabel("This section is reserved for a later prompt.")
        label.setObjectName("muted")
        self._root.addWidget(label)
        self._root.addStretch(1)


class ContentArea(QStackedWidget):
    def __init__(self, engine: GameEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pages: dict[str, BasePage] = {}
        self._add_page("dashboard", DashboardPage(engine))
        self._add_page("deals", DealsPage(engine))
        self._add_page("portfolio", PortfolioPage(engine))
        self._add_page("managers", CityManagersPage(engine))
        self._add_page("development", LandDevelopmentPage(engine))
        self._add_page("finance", FinancialsPage(engine))
        self._add_page("loans", LoanCentrePage(engine))
        self._add_page("tax", TaxPage(engine))
        self._add_page("cities", CitiesPage(engine))
        self._add_page("credit", CreditRatingPage(engine))
        self._add_page("reports", ReportsPage(engine))
        self._add_page("research", ResearchPage(engine))
        self._add_page("competitors", CompetitorsPage(engine))
        self._add_page("settings", SettingsPage(engine))
        self.show_page("dashboard")

    def show_page(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        self.setCurrentWidget(page)
        page.refresh()

    def refresh(self) -> None:
        page = self.currentWidget()
        if isinstance(page, BasePage):
            page.refresh()

    def refresh_live(self) -> None:
        page = self.currentWidget()
        if isinstance(page, BasePage) and page.live_refresh:
            page.refresh()

    def _add_page(self, key: str, page: BasePage) -> None:
        self._pages[key] = page
        self.addWidget(page)
