# ui/dialogs.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from world.models import City, Country
from world.system import WorldSystem


class CitySelectionDialog(QDialog):
    def __init__(self, world: WorldSystem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._world = world
        self._rows: list[tuple[Country, City]] = [
            (country, city) for country in self._world.countries for city in country.cities
        ]
        self._selected_city_id: str | None = None
        self.setWindowTitle("Select City")
        self.resize(820, 520)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search city or country")
        self._search.textChanged.connect(self._refresh_rows)

        self._country_filter = QComboBox()
        self._country_filter.addItem("All countries", "")
        for country in sorted(self._world.countries, key=lambda item: item.name):
            self._country_filter.addItem(country.name, country.country_id)
        self._country_filter.currentIndexChanged.connect(self._refresh_rows)

        self._sort = QComboBox()
        self._sort.addItem("Demand score", "demand")
        self._sort.addItem("Population", "population")
        self._sort.addItem("Property multiplier", "property")
        self._sort.currentIndexChanged.connect(self._refresh_rows)

        self._details = QLabel("Select a city to inspect its market statistics.")
        self._details.setObjectName("muted")
        self._details.setWordWrap(True)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ("City", "Country", "Population", "Property", "Growth", "Demand")
        )
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._update_details)
        self._table.itemDoubleClicked.connect(lambda _: self.accept())

        controls = QHBoxLayout()
        controls.addWidget(self._search)
        controls.addWidget(self._country_filter)
        controls.addWidget(self._sort)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(self._table)
        layout.addWidget(self._details)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self._refresh_rows()

    @property
    def selected_city_id(self) -> str | None:
        return self._selected_city_id

    def accept(self) -> None:
        self._update_details()
        if self._selected_city_id is None:
            return
        super().accept()

    def _refresh_rows(self) -> None:
        query = self._search.text().strip().lower()
        country_id = str(self._country_filter.currentData() or "")
        sort_key = str(self._sort.currentData())
        rows = [
            (country, city)
            for country, city in self._rows
            if (not country_id or country.country_id == country_id)
            and (
                not query
                or query in city.name.lower()
                or query in country.name.lower()
            )
        ]
        rows.sort(key=lambda row: self._sort_value(row[1], sort_key), reverse=True)

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for row_index, (country, city) in enumerate(rows):
            values = (
                city.name,
                country.name,
                f"{city.population:,}",
                f"{city.property_multiplier:.2f}x",
                f"{city.growth_rate * 100:.1f}%",
                f"{city.demand_score:.1f}",
            )
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, city.city_id)
                self._table.setItem(row_index, column_index, item)
        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()

    def _update_details(self) -> None:
        items = self._table.selectedItems()
        if not items:
            self._selected_city_id = None
            return

        city_id = str(items[0].data(Qt.ItemDataRole.UserRole))
        city = self._world.get_city(city_id)
        if city is None:
            self._selected_city_id = None
            return

        self._selected_city_id = city.city_id
        self._details.setText(
            f"{city.name}: population {city.population:,}, property {city.property_multiplier:.2f}x, "
            f"growth {city.growth_rate * 100:.1f}%, demand {city.demand_score:.1f}."
        )

    def _sort_value(self, city: City, sort_key: str) -> float:
        if sort_key == "population":
            return city.population
        if sort_key == "property":
            return city.property_multiplier
        return city.demand_score


class NewGameDialog(QDialog):
    def __init__(self, world: WorldSystem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._world = world
        self._hq_city_id = "new_york_city"
        self.setWindowTitle("New Game")
        self.resize(520, 210)

        self._company_name = QLineEdit("Platinum")
        city = self._world.get_city(self._hq_city_id)
        self._city_label = QLabel(city.name if city is not None else "New York City")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        city_picker = QPushButton("Select HQ City")
        city_picker.clicked.connect(self._select_city)

        form = QGridLayout()
        form.addWidget(QLabel("Company name"), 0, 0)
        form.addWidget(self._company_name, 0, 1)
        form.addWidget(QLabel("HQ city"), 1, 0)
        form.addWidget(self._city_label, 1, 1)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(city_picker)
        layout.addStretch(1)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def company_name(self) -> str:
        return self._company_name.text().strip()

    @property
    def starting_industry(self) -> str:
        return "real_estate"

    @property
    def hq_city_id(self) -> str:
        return self._hq_city_id

    def _select_city(self) -> None:
        dialog = CitySelectionDialog(self._world, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_city_id is not None:
            self._hq_city_id = dialog.selected_city_id
            city = self._world.get_city(self._hq_city_id)
            self._city_label.setText(city.name if city is not None else self._hq_city_id)


class DebugMoneyDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Developer Money")
        self.resize(360, 160)
        self._amount = QLineEdit("1000000")

        quick_row = QHBoxLayout()
        for label, value in (("$100k", 100000), ("$1M", 1000000), ("$10M", 10000000)):
            button = QPushButton(label)
            button.clicked.connect(lambda checked, amount=value: self._amount.setText(str(amount)))
            quick_row.addWidget(button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Add cash to holding company"))
        layout.addWidget(self._amount)
        layout.addLayout(quick_row)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def amount(self) -> int:
        return int(self._amount.text().replace("$", "").replace(",", "").strip())


class ReportBarGraph(QWidget):
    def __init__(self, values: dict[str, int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values = values
        self.setMinimumHeight(170)

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 20, -12, -24)
        if not self._values:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No report data")
            return
        maximum = max(abs(value) for value in self._values.values()) or 1
        width = max(8, rect.width() // max(1, len(self._values)) - 8)
        for index, (label, value) in enumerate(self._values.items()):
            x = rect.left() + index * (width + 8)
            height = round((abs(value) / maximum) * rect.height())
            y = rect.bottom() - height
            painter.setPen(QPen(Qt.GlobalColor.gray, 1))
            painter.drawText(x, max(rect.top() + 12, y - 4), self._money(value))
            painter.drawText(x, rect.bottom() + 18, label[:10])
            painter.fillRect(x, y, width, height, Qt.GlobalColor.darkGreen if value >= 0 else Qt.GlobalColor.darkRed)

    def _money(self, value: int) -> str:
        prefix = "-" if value < 0 else ""
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"{prefix}${absolute / 1_000_000:.1f}M"
        if absolute >= 1_000:
            return f"{prefix}${absolute / 1_000:.1f}K"
        return f"{prefix}${absolute}"


class ReportDialog(QDialog):
    def __init__(self, report: dict[str, object], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Monthly Report" if report.get("type") == "monthly" else "Quarterly Report")
        self.resize(780, 600)
        layout = QVBoxLayout()
        title = QLabel(str(self.windowTitle()))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        if report.get("type") == "monthly":
            income = {str(key): int(value) for key, value in dict(report.get("income", {})).items()}
            expenses = {str(key): int(value) for key, value in dict(report.get("expenses", {})).items()}
            summary = {str(key): value for key, value in dict(report.get("summary", {})).items()}
            layout.addWidget(ReportBarGraph({**income, **{key: -value for key, value in expenses.items()}}))
            layout.addWidget(self._table("Income", income))
            layout.addWidget(self._table("Expenses", expenses))
            layout.addWidget(self._table("Summary", summary))
        else:
            summary = {str(key): value for key, value in dict(report.get("summary", {})).items()}
            numeric = {key: int(value) for key, value in summary.items() if isinstance(value, int)}
            layout.addWidget(ReportBarGraph(numeric))
            layout.addWidget(self._table("Quarter", summary))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _table(self, title: str, rows: dict[str, object]) -> QTableWidget:
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels((title, "Value"))
        table.verticalHeader().setVisible(False)
        for row_index, (label, value) in enumerate(rows.items()):
            table.setItem(row_index, 0, QTableWidgetItem(str(label)))
            table.setItem(row_index, 1, QTableWidgetItem(self._display(value)))
        table.resizeColumnsToContents()
        return table

    def _display(self, value: object) -> str:
        if isinstance(value, int):
            return f"${value:,}"
        if isinstance(value, float):
            return f"{value * 100:.1f}%"
        return str(value)
