from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox

from app.config_store import ConfigStore
from app.keyring_store import KeyringStore, KeyringUnavailable
from app.profiles import AuthType, SSHProfile
from app.settings import TerminalSettings
from ui.connection_dialog import ConnectionDialog
from ui.profile_sidebar import ProfileSidebar
from ui.settings_dialog import SettingsDialog
from ui.sftp_panel import SftpPanel
from ui.tab_manager import TerminalTabManager
from terminal.font_selection import resolve_terminal_font_family


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kav SSH Terminal")
        self.setMinimumSize(980, 620)
        self.store = ConfigStore()
        self.settings = self.store.load_settings()
        self._upgrade_terminal_settings()
        self.profiles = self.store.load_profiles()
        self.keyring = KeyringStore()

        self.sidebar = ProfileSidebar()
        self.sidebar.set_profiles(self.profiles)
        self.sidebar.profile_activated.connect(self.connect_profile)
        self.sidebar.new_profile_requested.connect(self.open_connection_dialog)
        self.sidebar.edit_profile_requested.connect(self.edit_profile)
        self.sidebar.delete_profile_requested.connect(self.delete_profile)
        profiles_dock = QDockWidget("Profiles", self)
        profiles_dock.setWidget(self.sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, profiles_dock)

        self.sftp_panel = SftpPanel()
        sftp_dock = QDockWidget("SFTP", self)
        sftp_dock.setMinimumWidth(380)
        sftp_dock.setWidget(self.sftp_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, sftp_dock)

        self.tabs = TerminalTabManager(self.settings.terminal)
        self.tabs.session_activated.connect(self.sftp_panel.open_profile)
        self.tabs.session_cleared.connect(self.sftp_panel.clear_session)
        self.setCentralWidget(self.tabs)

        self._build_actions()
        self.resizeDocks([profiles_dock, sftp_dock], [280, 420], Qt.Orientation.Horizontal)
        self.statusBar().showMessage("Ready")

    def _build_actions(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        connect_action = QAction("Connect", self)
        settings_action = QAction("Settings", self)
        duplicate_action = QAction("Duplicate", self)
        connect_action.setStatusTip("Open a new SSH connection")
        settings_action.setStatusTip("Change terminal font settings")
        duplicate_action.setStatusTip("Duplicate the current live SSH tab")

        connect_action.triggered.connect(self.open_connection_dialog)
        settings_action.triggered.connect(self.open_settings_dialog)
        duplicate_action.triggered.connect(self.duplicate_current_session)

        toolbar.addAction(connect_action)
        toolbar.addAction(settings_action)
        toolbar.addAction(duplicate_action)

    def _upgrade_terminal_settings(self) -> None:
        terminal = self.settings.terminal
        changed = False
        legacy_defaults = {
            "font_family": "Courier New",
            "foreground": "#d8dee9",
            "background": "#101418",
            "cursor": "#f8f8f2",
            "selection": "#3d5a80",
        }
        if all(getattr(terminal, key) == value for key, value in legacy_defaults.items()):
            terminal = TerminalSettings(
                font_size=terminal.font_size,
                scrollback_lines=terminal.scrollback_lines,
                columns=terminal.columns,
                rows=terminal.rows,
            )
            changed = True
        if terminal.parser_backend != "pyte":
            terminal = terminal.model_copy(update={"parser_backend": "pyte"})
            changed = True
        resolved_font = resolve_terminal_font_family(terminal.font_family)
        if resolved_font != terminal.font_family:
            terminal = terminal.model_copy(update={"font_family": resolved_font})
            changed = True
        if changed:
            self.settings.terminal = terminal
            self.store.save_settings(self.settings)

    def open_connection_dialog(self) -> None:
        dialog = ConnectionDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        profile = dialog.profile()
        password = dialog.password()
        if dialog.should_save_profile():
            self.profiles.upsert(profile)
            self.store.save_profiles(self.profiles)
            self.sidebar.set_profiles(self.profiles)
        if dialog.should_save_password() and password:
            self._save_password(profile, password)
        self.tabs.add_ssh_tab(profile, password=password)

    def connect_profile(self, profile: SSHProfile) -> None:
        password = None
        if profile.auth_type == AuthType.PASSWORD:
            password = self._load_password(profile)
            if password is None:
                dialog = ConnectionDialog(profile=profile, parent=self)
                if dialog.exec() != dialog.DialogCode.Accepted:
                    return
                updated_profile = dialog.profile(existing_id=profile.id)
                if dialog.should_save_profile():
                    self.profiles.upsert(updated_profile)
                    self.store.save_profiles(self.profiles)
                    self.sidebar.set_profiles(self.profiles)
                    profile = updated_profile
                password = dialog.password()
                if dialog.should_save_password() and password:
                    self._save_password(profile, password)
        elif profile.auth_type == AuthType.INTERACTIVE:
            password = self._load_password(profile)
        self.tabs.add_ssh_tab(profile, password=password)

    def edit_profile(self, profile: SSHProfile) -> None:
        dialog = ConnectionDialog(profile=profile, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated_profile = dialog.profile(existing_id=profile.id)
        password = dialog.password()
        self.profiles.upsert(updated_profile)
        self.store.save_profiles(self.profiles)
        self.sidebar.set_profiles(self.profiles)

        if updated_profile.keyring_username != profile.keyring_username:
            self._delete_password(profile)
        if updated_profile.auth_type in (AuthType.PASSWORD, AuthType.INTERACTIVE):
            if dialog.should_save_password() and password:
                self._save_password(updated_profile, password)
        else:
            self._delete_password(profile)
            self._delete_password(updated_profile)

    def delete_profile(self, profile: SSHProfile) -> None:
        answer = QMessageBox.question(
            self,
            "Delete profile",
            f"Delete profile '{profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = self.profiles.remove(profile.id)
        if removed is None:
            return
        self.store.save_profiles(self.profiles)
        self.sidebar.set_profiles(self.profiles)
        self._delete_password(removed)

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings.terminal, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.settings.terminal = dialog.terminal_settings(self.settings.terminal)
        self.store.save_settings(self.settings)
        self.tabs.apply_terminal_settings(self.settings.terminal)

    def duplicate_current_session(self) -> None:
        if not self.tabs.duplicate_current_session():
            QMessageBox.information(
                self,
                "Duplicate tab",
                "Only live SSH profile tabs can be duplicated.",
            )

    def _save_password(self, profile: SSHProfile, password: str) -> None:
        try:
            self.keyring.set_password(profile, password)
        except KeyringUnavailable as exc:
            QMessageBox.warning(self, "Keyring unavailable", str(exc))

    def _load_password(self, profile: SSHProfile) -> str | None:
        try:
            return self.keyring.get_password(profile)
        except KeyringUnavailable:
            return None

    def _delete_password(self, profile: SSHProfile) -> None:
        try:
            self.keyring.delete_password(profile)
        except KeyringUnavailable:
            return
