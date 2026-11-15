from __future__ import annotations

import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QInputDialog, QLineEdit, QTabWidget

from app.profiles import SSHProfile
from app.settings import TerminalSettings
from ssh.ssh_client import AuthPrompt, SSHConnectionOptions, SshSessionRunner
from terminal.terminal_widget import TerminalWidget

HEBREW_PROOF_TEXT = "\n".join(
    [
        'echo "שלום עולם"',
        'echo "בדיקה בעברית עם English 123"',
        'echo "abc שלום def"',
        'echo "קובץ /var/www/html/index.html עודכן"',
        'echo "שרת production - מצב תקין"',
        "",
    ]
)


class _SessionSignals(QObject):
    output = Signal(str)
    status = Signal(str)
    error = Signal(str)
    auth_prompt = Signal(object)


@dataclass
class _AuthPromptEnvelope:
    prompt: AuthPrompt
    event: threading.Event
    response: str | None = None


class TerminalTabManager(QTabWidget):
    session_activated = Signal(object, object)
    session_cleared = Signal()

    def __init__(self, settings: TerminalSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setDocumentMode(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._emit_current_session)
        self._signals = _SessionSignals(self)
        self._signals.auth_prompt.connect(self._handle_auth_prompt)
        self._runners: dict[TerminalWidget, SshSessionRunner] = {}
        self._sessions: dict[TerminalWidget, tuple[SSHProfile, str | None]] = {}

    def add_hebrew_proof_tab(self) -> TerminalWidget:
        terminal = TerminalWidget(self.settings)
        terminal.feed(HEBREW_PROOF_TEXT.replace("\n", "\r\n"))
        self.addTab(terminal, "Hebrew RTL proof")
        self.setCurrentWidget(terminal)
        return terminal

    def add_ssh_tab(self, profile: SSHProfile, password: str | None = None) -> TerminalWidget:
        terminal = TerminalWidget(self.settings)
        signals = _SessionSignals(self)
        signals.output.connect(terminal.feed)
        signals.status.connect(lambda status: terminal.feed(f"\r\n[{status}]\r\n"))
        signals.error.connect(lambda error: terminal.feed(f"\r\n[SSH error] {error}\r\n"))

        options = SSHConnectionOptions(
            profile=profile,
            password=password,
            columns=terminal.buffer.size.columns,
            rows=terminal.buffer.size.rows,
        )
        runner = SshSessionRunner(
            options=options,
            on_data=signals.output.emit,
            on_status=signals.status.emit,
            on_error=lambda exc: signals.error.emit(str(exc)),
            on_auth_prompt=self._request_auth_prompt,
        )
        terminal.input_requested.connect(runner.send)
        terminal.terminal_resized.connect(runner.resize)
        self._runners[terminal] = runner
        self._sessions[terminal] = (profile, password)
        index = self.addTab(terminal, profile.name)
        self.setCurrentIndex(index)
        QTimer.singleShot(
            0,
            lambda: runner.resize(terminal.buffer.size.columns, terminal.buffer.size.rows),
        )
        runner.start()
        return terminal

    def duplicate_current_session(self) -> bool:
        current = self.currentWidget()
        if not isinstance(current, TerminalWidget):
            return False
        session = self._sessions.get(current)
        if not session:
            return False
        profile, password = session
        self.add_ssh_tab(profile, password=password)
        return True

    def apply_terminal_settings(self, settings: TerminalSettings) -> None:
        self.settings = settings
        for index in range(self.count()):
            widget = self.widget(index)
            if isinstance(widget, TerminalWidget):
                widget.apply_settings(settings)

    def close_tab(self, index: int) -> None:
        widget = self.widget(index)
        runner = self._runners.pop(widget, None) if isinstance(widget, TerminalWidget) else None
        if runner:
            runner.stop()
        if isinstance(widget, TerminalWidget):
            self._sessions.pop(widget, None)
        self.removeTab(index)
        if widget:
            widget.deleteLater()

    def _emit_current_session(self, index: int) -> None:
        widget = self.widget(index)
        if isinstance(widget, TerminalWidget) and widget in self._sessions:
            profile, password = self._sessions[widget]
            self.session_activated.emit(profile, password)
            return
        self.session_cleared.emit()

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
