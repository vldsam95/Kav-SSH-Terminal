from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget


class SplitPaneManager(QSplitter):
    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)

    def add_pane(self, widget: QWidget) -> None:
        self.addWidget(widget)
