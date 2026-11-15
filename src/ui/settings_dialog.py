from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from app.settings import DEFAULT_TERMINAL_THEME, TERMINAL_THEMES, TerminalSettings
from terminal.font_selection import resolve_terminal_font_family


class SettingsDialog(QDialog):
    def __init__(self, settings: TerminalSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(TERMINAL_THEMES.keys())
        current_theme = settings.theme_name
        if current_theme not in TERMINAL_THEMES:
            current_theme = DEFAULT_TERMINAL_THEME
        self.theme_combo.setCurrentText(current_theme)
        self.font_combo = QFontComboBox()
        self.font_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        self.font_combo.setCurrentFont(QFont(resolve_terminal_font_family(settings.font_family)))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(settings.font_size)

        form = QFormLayout()
        form.addRow("Theme", self.theme_combo)
        form.addRow("Terminal font", self.font_combo)
        form.addRow("Font size", self.font_size_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def terminal_settings(self, current: TerminalSettings) -> TerminalSettings:
        theme_name = self.theme_combo.currentText()
        theme = TERMINAL_THEMES.get(theme_name, TERMINAL_THEMES[DEFAULT_TERMINAL_THEME])
        return current.model_copy(
            update={
                "theme_name": theme_name,
                "font_family": resolve_terminal_font_family(self.font_combo.currentFont().family()),
                "font_size": self.font_size_spin.value(),
                **theme,
            }
        )
