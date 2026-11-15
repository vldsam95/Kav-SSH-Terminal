from __future__ import annotations

import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TypeVar

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.profiles import SSHProfile
from ssh.sftp_client import RemoteFile, SftpClient
from ssh.sftp_session import SftpSession
from ssh.ssh_client import AuthPrompt
from ui.text_editor_dialog import TextEditorDialog


MAX_EDIT_BYTES = 5 * 1024 * 1024
T = TypeVar("T")
TEXT_EXTENSIONS = {
    ".bashrc",
    ".conf",
    ".config",
    ".css",
    ".csv",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".log",
    ".md",
    ".php",
    ".py",
    ".service",
    ".sh",
    ".sql",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


class _SftpSignals(QObject):
    files_loaded = Signal(int, str, object)
    error = Signal(int, str)
    file_loaded = Signal(object, object)
    transfer_done = Signal(str)
    transfer_error = Signal(str)
    auth_prompt = Signal(object)


@dataclass
class _AuthPromptEnvelope:
    prompt: AuthPrompt
    event: threading.Event
    response: str | None = None


class SftpPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SftpPanel")
        self.setMinimumWidth(360)
        self._profile: SSHProfile | None = None
        self._password: str | None = None
        self._sftp_session: SftpSession | None = None
        self._load_generation = 0
        self._loading_tick = 0
        self._signals = _SftpSignals(self)
        self._signals.files_loaded.connect(self._apply_files)
        self._signals.error.connect(self._show_error)
        self._signals.file_loaded.connect(self._show_text_editor)
        self._signals.transfer_done.connect(self._show_transfer_done)
        self._signals.transfer_error.connect(self._show_transfer_error)
        self._signals.auth_prompt.connect(self._handle_auth_prompt)
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(350)
        self._loading_timer.timeout.connect(self._animate_loading)

        self.path_edit = QLineEdit("~")
        self.refresh_button = QPushButton("Refresh")
        self.upload_button = QPushButton("Upload")
        self.download_button = QPushButton("Download")
        self.edit_button = QPushButton("Edit")
        self.rename_button = QPushButton("Rename")
        self.delete_button = QPushButton("Delete")
        self.compress_button = QPushButton("Compress ZIP")
        self.status_label = QLabel("Open an SSH session to browse SFTP.")
        self.table = QTableWidget(0, 3)
        self._folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._file_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Permissions"])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 220)
        self.refresh_button.clicked.connect(self.refresh)
        self.path_edit.returnPressed.connect(self.refresh)
        self.table.itemDoubleClicked.connect(self._open_item)
        self.table.itemSelectionChanged.connect(self._sync_transfer_buttons)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.upload_button.clicked.connect(self.upload)
        self.download_button.clicked.connect(self.download)
        self.edit_button.clicked.connect(self.edit)
        self.rename_button.clicked.connect(self.rename)
        self.delete_button.clicked.connect(self.delete)
        self.compress_button.clicked.connect(self.compress_zip)
        self._sync_transfer_buttons()

        top = QHBoxLayout()
        top.addWidget(self.path_edit)
        top.addWidget(self.refresh_button)
        top.addWidget(self.upload_button)
        top.addWidget(self.download_button)

        actions = QHBoxLayout()
        actions.addWidget(self.edit_button)
        actions.addWidget(self.rename_button)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.compress_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addLayout(top)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)

    def open_profile(self, profile: SSHProfile, password: str | None) -> None:
        if self._profile is None or self._session_key(profile, password) != self._active_session_key():
            self._close_sftp_session()
        self._profile = profile
        self._password = password
        self.path_edit.setText(profile.default_remote_path or "~")
        self._sync_transfer_buttons()
        self.refresh()

    def clear_session(self) -> None:
        self._close_sftp_session()
        self._profile = None
        self._password = None
        self._load_generation += 1
        self.table.setRowCount(0)
        self.status_label.setText("Open an SSH session to browse SFTP.")
        self.refresh_button.setEnabled(True)
        self._loading_timer.stop()
        self._sync_transfer_buttons()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override.
        self._close_sftp_session()
        super().closeEvent(event)

    def _ensure_sftp_session(self) -> SftpSession | None:
        if self._profile is None:
            return None
        expected_key = self._session_key(self._profile, self._password)
        if self._sftp_session is None or self._sftp_session.key != expected_key:
            self._close_sftp_session()
            self._sftp_session = SftpSession(
                profile=self._profile,
                password=self._password,
                on_auth_prompt=self._request_auth_prompt,
            )
        return self._sftp_session

    def _close_sftp_session(self) -> None:
        if self._sftp_session is None:
            return
        session = self._sftp_session
        self._sftp_session = None
        session.close()

    def _active_session_key(self) -> tuple[object, ...] | None:
        return self._sftp_session.key if self._sftp_session is not None else None

    @staticmethod
    def _session_key(profile: SSHProfile, password: str | None) -> tuple[object, ...]:
        return (
            profile.id,
            profile.host,
            profile.port,
            profile.username,
            profile.auth_type,
            password or "",
        )

    def _submit_sftp(
        self,
        operation: Callable[[SftpClient], Awaitable[T]],
        on_success: Callable[[T], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        session = self._ensure_sftp_session()
        if session is None:
            return
        future = session.submit(operation)
        future.add_done_callback(
            lambda done: self._handle_sftp_result(done, on_success, on_error)
        )

    def _handle_sftp_result(
        self,
        future: Future[T],
        on_success: Callable[[T], None],
        on_error: Callable[[str], None] | None,
    ) -> None:
        try:
            result = future.result()
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            if on_error is not None:
                on_error(message)
            else:
                self._signals.transfer_error.emit(message)
            return
        on_success(result)

    def refresh(self) -> None:
        if self._profile is None:
            self.clear_session()
            return

        self._load_generation += 1
        generation = self._load_generation
        display_path = self.path_edit.text().strip() or "~"
        request_path = self._request_path(display_path)
        self._loading_tick = 0
        self.status_label.setText(f"Loading {display_path}...")
        self._loading_timer.start()
        self.refresh_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self._submit_sftp(
            lambda client: client.listdir(request_path),
            lambda files: self._signals.files_loaded.emit(generation, display_path, files),
            lambda message: self._signals.error.emit(generation, message),
        )

    def set_files(self, files: list[RemoteFile]) -> None:
        self.table.setRowCount(len(files))
        for row, file in enumerate(files):
            icon = self._folder_icon if file.is_dir else self._file_icon
            name_item = QTableWidgetItem(icon, file.name)
            name_item.setToolTip(file.name)
            name_item.setData(Qt.ItemDataRole.UserRole, file)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(self._display_size(file)))
            permissions = "" if file.permissions is None else format(file.permissions, "o")
            self.table.setItem(row, 2, QTableWidgetItem(permissions))
        self._resize_name_column(files)
        self._sync_transfer_buttons()

    def upload(self) -> None:
        if self._profile is None:
            return
        local_path, _ = QFileDialog.getOpenFileName(self, "Upload file")
        if not local_path:
            return

        local = Path(local_path)
        display_path = self.path_edit.text().strip() or "~"
        remote_dir = self._request_path(display_path)
        remote_path = self._remote_child_path(remote_dir, local.name)
        self.status_label.setText(f"Uploading {local.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.upload(str(local), remote_path),
            lambda _result: self._signals.transfer_done.emit(f"Uploaded {local.name}"),
        )

    def download(self) -> None:
        file = self._selected_file()
        if self._profile is None or file is None or file.is_dir:
            return
        local_path, _ = QFileDialog.getSaveFileName(self, "Download file", file.name)
        if not local_path:
            return

        self.status_label.setText(f"Downloading {file.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.download(file.path, local_path),
            lambda _result: self._signals.transfer_done.emit(f"Downloaded {Path(local_path).name}"),
        )

    def edit(self) -> None:
        file = self._selected_file()
        if self._profile is None or file is None or file.is_dir or not self._can_edit(file):
            return
        self.status_label.setText(f"Opening {file.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.read_file(file.path, max_bytes=MAX_EDIT_BYTES),
            lambda data: self._signals.file_loaded.emit(file, data),
        )

    def rename(self) -> None:
        file = self._selected_file()
        if self._profile is None or file is None or file.name == "..":
            return
        new_name, accepted = QInputDialog.getText(self, "Rename", "New name:", text=file.name)
        new_name = new_name.strip()
        if not accepted or not new_name or new_name == file.name or "/" in new_name:
            return
        new_path = self._remote_sibling_path(file.path, new_name)
        self.status_label.setText(f"Renaming {file.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.rename(file.path, new_path),
            lambda _result: self._signals.transfer_done.emit(
                f"Renamed {file.name} to {new_name}"
            ),
        )

    def delete(self) -> None:
        file = self._selected_file()
        if self._profile is None or file is None or file.name == "..":
            return
        kind = "folder" if file.is_dir else "file"
        answer = QMessageBox.question(
            self,
            "Delete",
            f"Delete {kind} '{file.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.status_label.setText(f"Deleting {file.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.delete_path(file.path, is_dir=file.is_dir),
            lambda _result: self._signals.transfer_done.emit(f"Deleted {file.name}"),
        )

    def compress_zip(self) -> None:
        file = self._selected_file()
        if self._profile is None or file is None or not file.is_dir or file.name == "..":
            return
        default_name = f"{file.name.rstrip('/')}.zip"
        archive_name, accepted = QInputDialog.getText(
            self,
            "Compress ZIP",
            "Archive name:",
            text=default_name,
        )
        archive_name = archive_name.strip()
        if not accepted or not archive_name or "/" in archive_name:
            return
        archive_path = self._remote_sibling_path(file.path, archive_name)
        self.status_label.setText(f"Compressing {file.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.compress_directory_zip(file.path, archive_path),
            lambda _result: self._signals.transfer_done.emit(f"Created {archive_name}"),
        )

    def _request_auth_prompt(self, prompt: AuthPrompt) -> str | None:
        envelope = _AuthPromptEnvelope(prompt=prompt, event=threading.Event())
        self._signals.auth_prompt.emit(envelope)
        envelope.event.wait()
        return envelope.response

    def _handle_auth_prompt(self, envelope: _AuthPromptEnvelope) -> None:
        prompt = envelope.prompt
        label = prompt.prompt
        if prompt.instructions:
            label = f"{prompt.instructions}\n\n{label}"
        mode = QLineEdit.EchoMode.Normal if prompt.echo else QLineEdit.EchoMode.Password
        response, accepted = QInputDialog.getText(
            self,
            prompt.title,
            label,
            mode,
            prompt.default_response,
        )
        envelope.response = response if accepted else None
        envelope.event.set()

    def _apply_files(self, generation: int, display_path: str, files: object) -> None:
        if generation != self._load_generation:
            return
        self._loading_timer.stop()
        typed_files = self._files_with_parent(display_path, list(files))
        self.set_files(typed_files)
        self.status_label.setText(f"{len(typed_files)} items in {display_path}")
        self.refresh_button.setEnabled(True)
        self._sync_transfer_buttons()

    def _show_error(self, generation: int, message: str) -> None:
        if generation != self._load_generation:
            return
        self._loading_timer.stop()
        self.table.setRowCount(0)
        self.status_label.setText(f"SFTP error: {message}")
        self.refresh_button.setEnabled(True)
        self._sync_transfer_buttons()

    def _show_transfer_done(self, message: str) -> None:
        self.status_label.setText(message)
        self._set_transfer_busy(False)
        self.refresh()

    def _show_transfer_error(self, message: str) -> None:
        self.status_label.setText(f"SFTP transfer error: {message}")
        self._set_transfer_busy(False)

    def _show_text_editor(self, file: object, data: object) -> None:
        self._set_transfer_busy(False)
        if not isinstance(file, RemoteFile) or not isinstance(data, bytes):
            self.status_label.setText("SFTP edit error: invalid file data")
            return
        if self._profile is None:
            self.status_label.setText("SFTP edit cancelled: no active session")
            return
        try:
            text, encoding = self._decode_text_file(data, file.name)
        except ValueError as exc:
            self.status_label.setText(f"SFTP edit error: {exc}")
            return

        dialog = TextEditorDialog(file.path, text, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            self.status_label.setText(f"Edit cancelled for {file.name}")
            return

        payload = dialog.text().encode(encoding, errors="replace")
        self.status_label.setText(f"Saving {file.name}...")
        self._set_transfer_busy(True)
        self._submit_sftp(
            lambda client: client.write_file(file.path, payload),
            lambda _result: self._signals.transfer_done.emit(f"Saved {file.name}"),
        )

    def _open_item(self, item: QTableWidgetItem) -> None:
        name_item = self.table.item(item.row(), 0)
        if name_item is None:
            return
        file = name_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(file, RemoteFile):
            return
        if file.is_dir:
            self.path_edit.setText(file.path)
            self.refresh()
            return
        self.edit()

    def _show_context_menu(self, point) -> None:
        menu = QMenu(self)
        selected = self._selected_file()
        edit_action = menu.addAction("Edit")
        download_action = menu.addAction("Download")
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        compress_action = menu.addAction("Compress ZIP")
        edit_action.setEnabled(selected is not None and self._can_edit(selected))
        download_action.setEnabled(selected is not None and not selected.is_dir)
        rename_action.setEnabled(selected is not None and selected.name != "..")
        delete_action.setEnabled(selected is not None and selected.name != "..")
        compress_action.setEnabled(
            selected is not None and selected.is_dir and selected.name != ".."
        )
        action = menu.exec(self.table.viewport().mapToGlobal(point))
        if action == edit_action:
            self.edit()
        elif action == download_action:
            self.download()
        elif action == rename_action:
            self.rename()
        elif action == delete_action:
            self.delete()
        elif action == compress_action:
            self.compress_zip()

    def _animate_loading(self) -> None:
        self._loading_tick = (self._loading_tick + 1) % 4
        path = self.path_edit.text().strip() or "~"
        self.status_label.setText(f"Loading {path}{'.' * self._loading_tick}")

    def _resize_name_column(self, files: list[RemoteFile]) -> None:
        if not files:
            self.table.setColumnWidth(0, 220)
            return
        metrics = self.table.fontMetrics()
        widest_name = max(files, key=lambda file: metrics.horizontalAdvance(file.name)).name
        width = metrics.horizontalAdvance(widest_name) + 44
        self.table.setColumnWidth(0, max(260, min(width, 620)))

    def _sync_transfer_buttons(self) -> None:
        has_profile = self._profile is not None
        selected = self._selected_file()
        selected_real = selected is not None and selected.name != ".."
        self.upload_button.setEnabled(has_profile)
        self.download_button.setEnabled(
            has_profile and selected is not None and not selected.is_dir
        )
        self.edit_button.setEnabled(has_profile and selected is not None and self._can_edit(selected))
        self.rename_button.setEnabled(has_profile and selected_real)
        self.delete_button.setEnabled(has_profile and selected_real)
        self.compress_button.setEnabled(
            has_profile and selected_real and selected is not None and selected.is_dir
        )

    def _set_transfer_busy(self, busy: bool) -> None:
        if busy:
            self.refresh_button.setEnabled(False)
            self.upload_button.setEnabled(False)
            self.download_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.rename_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.compress_button.setEnabled(False)
            return
        self.refresh_button.setEnabled(True)
        self._sync_transfer_buttons()

    def _selected_file(self) -> RemoteFile | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        file = item.data(Qt.ItemDataRole.UserRole)
        return file if isinstance(file, RemoteFile) else None

    def _can_edit(self, file: RemoteFile) -> bool:
        if file.is_dir or file.name == "..":
            return False
        if file.size > MAX_EDIT_BYTES:
            return False
        name = file.name.casefold()
        suffix = PurePosixPath(file.name).suffix.casefold()
        return name in TEXT_EXTENSIONS or suffix in TEXT_EXTENSIONS or file.size <= 256 * 1024

    def _files_with_parent(self, display_path: str, files: list[RemoteFile]) -> list[RemoteFile]:
        if display_path in ("", ".", "~", "/"):
            return files
        parent = RemoteFile(
            name="..",
            path=self._parent_path(display_path),
            size=0,
            is_dir=True,
        )
        return [parent, *files]

    @staticmethod
    def _display_size(file: RemoteFile) -> str:
        if file.is_dir:
            return ""
        size = file.size
        if size < 10_000:
            return f"{size:,} B"
        units = [
            ("GB", 1024**3),
            ("MB", 1024**2),
            ("KB", 1024),
        ]
        for suffix, factor in units:
            if size >= factor:
                return f"{size / factor:.1f} {suffix}"
        return f"{size:,} B"

    @staticmethod
    def _parent_path(path: str) -> str:
        if path.startswith("~/"):
            parent = PurePosixPath(path[2:]).parent.as_posix()
            return "~" if parent == "." else f"~/{parent}"
        if path.startswith("./"):
            parent = PurePosixPath(path[2:]).parent.as_posix()
            return "." if parent == "." else f"./{parent}"
        if path.startswith("/"):
            parent = PurePosixPath(path).parent.as_posix()
            return parent if parent else "/"
        parent = PurePosixPath(path).parent.as_posix()
        return "." if parent == "." else parent

    @staticmethod
    def _request_path(path: str) -> str:
        if path in ("", "~"):
            return "."
        if path.startswith("~/"):
            return f"./{path[2:]}"
        return path

    @staticmethod
    def _remote_child_path(parent: str, child_name: str) -> str:
        if parent in ("", "."):
            return f"./{child_name}"
        return f"{parent.rstrip('/')}/{child_name}"

    @staticmethod
    def _remote_sibling_path(path: str, new_name: str) -> str:
        parent = PurePosixPath(path).parent.as_posix()
        if parent in ("", "."):
            return f"./{new_name}"
        return f"{parent.rstrip('/')}/{new_name}"

    @staticmethod
    def _decode_text_file(data: bytes, name: str) -> tuple[str, str]:
        if b"\x00" in data:
            raise ValueError("binary files cannot be edited in-app")
        normalized_name = name.casefold()
        suffix = PurePosixPath(name).suffix.casefold()
        if (
            normalized_name not in TEXT_EXTENSIONS
            and suffix not in TEXT_EXTENSIONS
            and not SftpPanel._looks_like_text(data)
        ):
            raise ValueError("file does not look like a text file")
        for encoding in ("utf-8-sig", "utf-8", "cp1255"):
            try:
                return data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        return data.decode("latin-1"), "latin-1"

    @staticmethod
    def _looks_like_text(data: bytes) -> bool:
        if not data:
            return True
        sample = data[:4096]
        allowed_controls = {9, 10, 13, 27}
        control_count = sum(byte < 32 and byte not in allowed_controls for byte in sample)
        return control_count / len(sample) < 0.05
