# config/theme.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    window: str
    panel: str
    panel_alt: str
    panel_deep: str
    text: str
    muted_text: str
    accent: str
    accent_alt: str
    border: str
    button: str
    button_hover: str
    danger: str
    chart_grid: str
    font_size: int
    row_padding: int
    panel_radius: int


class ThemeManager:
    def __init__(self, themes: tuple[Theme, ...], active_theme: str) -> None:
        self._themes = {theme.name: theme for theme in themes}
        self._active_theme = active_theme

    @classmethod
    def default(cls) -> ThemeManager:
        themes = (
            Theme(
                name="Executive",
                window="#101418",
                panel="#171d22",
                panel_alt="#202830",
                panel_deep="#0c0f12",
                text="#edf2f4",
                muted_text="#9faab3",
                accent="#d6a84f",
                accent_alt="#78a6c8",
                border="#303943",
                button="#26313a",
                button_hover="#33414d",
                danger="#c75f5f",
                chart_grid="#2f3942",
                font_size=12,
                row_padding=4,
                panel_radius=2,
            ),
            Theme(
                name="Bloomberg",
                window="#080808",
                panel="#111111",
                panel_alt="#1c1c1c",
                panel_deep="#050505",
                text="#f0f0e8",
                muted_text="#a7a28d",
                accent="#ff9f1a",
                accent_alt="#2f9cff",
                border="#35312a",
                button="#1d1b17",
                button_hover="#2a251d",
                danger="#e05f43",
                chart_grid="#332b1f",
                font_size=11,
                row_padding=3,
                panel_radius=0,
            ),
            Theme(
                name="Financial Terminal",
                window="#06110b",
                panel="#0b1a12",
                panel_alt="#102719",
                panel_deep="#030905",
                text="#d9ffe4",
                muted_text="#75a684",
                accent="#00d26a",
                accent_alt="#5eb6ff",
                border="#21452d",
                button="#102318",
                button_hover="#173522",
                danger="#ff5f56",
                chart_grid="#173522",
                font_size=12,
                row_padding=3,
                panel_radius=0,
            ),
            Theme(
                name="Corporate Light",
                window="#f4f6f8",
                panel="#ffffff",
                panel_alt="#e8edf2",
                panel_deep="#f9fbfc",
                text="#17202a",
                muted_text="#65717f",
                accent="#2457a6",
                accent_alt="#487c5b",
                border="#c9d2dc",
                button="#eef2f6",
                button_hover="#dfe7ef",
                danger="#b44747",
                chart_grid="#d7e0e8",
                font_size=12,
                row_padding=5,
                panel_radius=4,
            ),
        )
        return cls(themes=themes, active_theme="Executive")

    @property
    def active_theme(self) -> Theme:
        return self._themes[self._active_theme]

    @property
    def theme_names(self) -> tuple[str, ...]:
        return tuple(self._themes)

    def set_active_theme(self, name: str) -> None:
        if name not in self._themes:
            raise ValueError(f"Unknown theme: {name}")

        self._active_theme = name

    def current_stylesheet(self) -> str:
        theme = self.active_theme
        return f"""
            QWidget {{
                background-color: {theme.window};
                color: {theme.text};
                font-family: Segoe UI, Arial, sans-serif;
                font-size: {theme.font_size}px;
            }}

            QFrame#sidebar,
            QFrame#timeBar {{
                background-color: {theme.panel};
                border: 1px solid {theme.border};
            }}

            QStackedWidget#contentArea {{
                background-color: {theme.window};
            }}

            QFrame#panel,
            QFrame#metric,
            QFrame#metricCard,
            QFrame#chartPanel,
            QFrame#topStat {{
                background-color: {theme.panel};
                border: 1px solid {theme.border};
                border-radius: {theme.panel_radius}px;
            }}

            QLabel#pageTitle {{
                color: {theme.text};
                font-size: 16px;
                font-weight: 600;
            }}

            QLabel#sectionTitle {{
                color: {theme.text};
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#brandTitle {{
                color: {theme.text};
                font-size: 18px;
                font-weight: 700;
            }}

            QLabel#metricLabel {{
                color: {theme.muted_text};
                font-size: 10px;
                font-weight: 600;
            }}

            QLabel#metricValue {{
                color: {theme.text};
                font-size: 14px;
                font-weight: 650;
            }}

            QLabel#muted {{
                color: {theme.muted_text};
            }}

            QPushButton {{
                background-color: {theme.button};
                border: 1px solid {theme.border};
                border-radius: {theme.panel_radius}px;
                padding: {theme.row_padding}px {theme.row_padding + 3}px;
            }}

            QPushButton:hover {{
                background-color: {theme.button_hover};
            }}

            QPushButton:checked {{
                background-color: {theme.panel_alt};
                color: {theme.text};
                border-color: {theme.accent};
            }}

            QPushButton#primaryButton {{
                border-color: {theme.accent};
            }}

            QTableWidget {{
                background-color: {theme.panel_deep};
                alternate-background-color: {theme.panel};
                border: 1px solid {theme.border};
                gridline-color: {theme.border};
                selection-background-color: {theme.panel_alt};
                selection-color: {theme.text};
            }}

            QHeaderView::section {{
                background-color: {theme.panel_alt};
                color: {theme.muted_text};
                border: none;
                border-right: 1px solid {theme.border};
                border-bottom: 1px solid {theme.border};
                padding: {theme.row_padding}px;
                font-weight: 600;
            }}

            QLineEdit,
            QComboBox {{
                background-color: {theme.panel_deep};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: {theme.panel_radius}px;
                padding: {theme.row_padding}px;
            }}

            QStatusBar {{
                background-color: {theme.panel};
                color: {theme.muted_text};
            }}
        """
