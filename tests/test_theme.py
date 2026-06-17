# tests/test_theme.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from config.theme import ThemeManager


def test_theme_manager_exposes_management_ui_presets() -> None:
    manager = ThemeManager.default()

    assert manager.theme_names == (
        "Executive",
        "Bloomberg",
        "Financial Terminal",
        "Corporate Light",
    )

    manager.set_active_theme("Bloomberg")

    assert manager.active_theme.name == "Bloomberg"
    assert "QTableWidget" in manager.current_stylesheet()
