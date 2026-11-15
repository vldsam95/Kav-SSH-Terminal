from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.profiles import AuthType, SSHProfile


class ConnectionDialog(QDialog):
    def __init__(self, profile: SSHProfile | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connect")
        self.setMinimumWidth(480)
        self.name_edit = QLineEdit(profile.name if profile else "")
        self.host_edit = QLineEdit(profile.host if profile else "")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(profile.port if profile else 22)
        self.username_edit = QLineEdit(profile.username if profile else "")
        self.auth_combo = QComboBox()
        self.auth_combo.addItem("Password", AuthType.PASSWORD.value)
        self.auth_combo.addItem("2FA / keyboard interactive", AuthType.INTERACTIVE.value)
        self.auth_combo.addItem("Private key", AuthType.PRIVATE_KEY.value)
        self.auth_combo.addItem("SSH agent", AuthType.AGENT.value)
        if profile:
            current_auth_index = self.auth_combo.findData(profile.auth_type.value)
            self.auth_combo.setCurrentIndex(max(0, current_auth_index))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_path_edit = QLineEdit(profile.private_key_path if profile else "")
        self.remote_path_edit = QLineEdit(profile.default_remote_path if profile else "~")
        self.group_edit = QLineEdit(profile.group or "" if profile else "")
        self.tags_edit = QLineEdit(", ".join(profile.tags) if profile else "")
        self.save_profile_check = QCheckBox("Save profile")
        self.save_profile_check.setChecked(True)
        self.save_password_check = QCheckBox("Save password in OS keychain")
        current_auth_type = profile.auth_type if profile else AuthType.PASSWORD
        self.save_password_check.setChecked(
            current_auth_type in (AuthType.PASSWORD, AuthType.INTERACTIVE)
        )

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_key)
        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.key_path_edit)
        key_layout.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Profile name", self.name_edit)
        form.addRow("Host", self.host_edit)
        form.addRow("Port", self.port_spin)
        form.addRow("Username", self.username_edit)
        form.addRow("Auth", self.auth_combo)
        form.addRow("Password", self.password_edit)
        form.addRow("Private key", key_row)
        form.addRow("Default path", self.remote_path_edit)
        form.addRow("Group", self.group_edit)
        form.addRow("Tags", self.tags_edit)
        form.addRow("", self.save_profile_check)
        form.addRow("", self.save_password_check)

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

        self.auth_combo.currentIndexChanged.connect(self._sync_auth_fields)
        self._sync_auth_fields()

    def profile(self, existing_id: str | None = None) -> SSHProfile:
        auth_type = AuthType(self.auth_combo.currentData())
        values = {
            "name": self.name_edit.text() or self.host_edit.text(),
            "host": self.host_edit.text(),
            "port": self.port_spin.value(),
            "username": self.username_edit.text(),
            "auth_type": auth_type,
            "private_key_path": self.key_path_edit.text() or None,
            "default_remote_path": self.remote_path_edit.text() or "~",
            "group": self.group_edit.text() or None,
            "tags": self.tags_edit.text(),
        }
        if existing_id:
            values["id"] = existing_id
        return SSHProfile(**values)

    def password(self) -> str | None:
        return self.password_edit.text() or None

    def should_save_profile(self) -> bool:
        return self.save_profile_check.isChecked()

    def should_save_password(self) -> bool:
        return self.save_password_check.isChecked()

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select private key")
        if path:
            self.key_path_edit.setText(path)

    def _sync_auth_fields(self) -> None:
        auth_type = AuthType(self.auth_combo.currentData())
        password_like = auth_type in (AuthType.PASSWORD, AuthType.INTERACTIVE)
        self.password_edit.setEnabled(password_like)
        self.save_password_check.setEnabled(password_like)
        self.key_path_edit.setEnabled(auth_type == AuthType.PRIVATE_KEY)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override.
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)
