from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.profiles import ProfileCollection, SSHProfile


class ProfileSidebar(QWidget):
    profile_activated = Signal(object)
    new_profile_requested = Signal()
    edit_profile_requested = Signal(object)
    delete_profile_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ProfileSidebar")
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.new_button = QPushButton("Connect")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.new_button.clicked.connect(self.new_profile_requested.emit)
        self.edit_button.clicked.connect(self._emit_edit_profile)
        self.delete_button.clicked.connect(self._emit_delete_profile)
        self.list_widget.itemDoubleClicked.connect(self._emit_profile)
        self.list_widget.itemSelectionChanged.connect(self._sync_buttons)

        actions = QHBoxLayout()
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self.new_button)
        layout.addWidget(self.list_widget)
        layout.addLayout(actions)
        self._sync_buttons()

    def set_profiles(self, collection: ProfileCollection) -> None:
        self.list_widget.clear()
        for profile in collection.profiles:
            label = f"{profile.name}  ({profile.username}@{profile.host})"
            item = QListWidgetItem(label)
            item.setData(256, profile)
            self.list_widget.addItem(item)

    def _emit_profile(self, item: QListWidgetItem) -> None:
        profile: SSHProfile = item.data(256)
        self.profile_activated.emit(profile)

    def _emit_edit_profile(self) -> None:
        profile = self._selected_profile()
        if profile is not None:
            self.edit_profile_requested.emit(profile)

    def _emit_delete_profile(self) -> None:
        profile = self._selected_profile()
        if profile is not None:
            self.delete_profile_requested.emit(profile)

    def _selected_profile(self) -> SSHProfile | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        profile = item.data(256)
        return profile if isinstance(profile, SSHProfile) else None

    def _sync_buttons(self) -> None:
        has_selection = self._selected_profile() is not None
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
