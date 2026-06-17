# ui/navigation.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout


@dataclass(frozen=True, slots=True)
class NavigationItem:
    key: str
    label: str


class SidebarNavigation(QFrame):
    section_changed = pyqtSignal(str)

    def __init__(self, items: tuple[NavigationItem, ...], parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(184)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self.setLayout(layout)

        title = QLabel("Property Empire")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Investment Office")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)

        for index, item in enumerate(items):
            button = QPushButton(item.label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, key=item.key: self._emit_section(key))
            self._button_group.addButton(button)
            layout.addWidget(button)

            if index == 0:
                button.setChecked(True)

        layout.addStretch(1)

    def _emit_section(self, key: str) -> None:
        self.section_changed.emit(key)
