from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

from terminal.font_selection import resolve_terminal_font_family


class TextEditorDialog(QDialog):
    def __init__(self, path: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit {path}")
        self.resize(900, 650)

        self.path_label = QLabel(path)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setFont(QFont(resolve_terminal_font_family("Cascadia Mono"), 11))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.path_label)
        layout.addWidget(self.editor)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.editor.toPlainText()
