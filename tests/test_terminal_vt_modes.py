from __future__ import annotations

from PySide6.QtCore import Qt

from terminal.ansi_parser import SimpleAnsiParser
from terminal.keyboard_input import qt_key_event_to_terminal_sequence
from terminal.terminal_buffer import TerminalBuffer


class _KeyEvent:
    def __init__(self, key, text: str = "", modifiers=Qt.KeyboardModifier.NoModifier) -> None:
        self._key = key
        self._text = text
        self._modifiers = modifiers

    def key(self):
        return self._key

    def text(self) -> str:
        return self._text

    def modifiers(self):
        return self._modifiers


def test_private_modes_track_application_cursor_bracketed_paste_and_mouse() -> None:
    buffer = TerminalBuffer(columns=20, rows=5, backend="pyte")

    buffer.feed("\x1b[?1h\x1b[?2004h\x1b[?1002h\x1b[?1006h")

    assert buffer.application_cursor_keys is True
    assert buffer.bracketed_paste is True
    assert buffer.mouse_tracking == "button"
    assert buffer.mouse_sgr is True

    buffer.feed("\x1b[?1l\x1b[?2004l\x1b[?1002l\x1b[?1006l")

    assert buffer.application_cursor_keys is False
    assert buffer.bracketed_paste is False
    assert buffer.mouse_tracking == "off"
    assert buffer.mouse_sgr is False


def test_application_cursor_keys_use_ss3_sequences() -> None:
    event = _KeyEvent(Qt.Key.Key_Up)

    assert qt_key_event_to_terminal_sequence(event) == "\x1b[A"
    assert qt_key_event_to_terminal_sequence(event, application_cursor_keys=True) == "\x1bOA"


def test_simple_parser_insert_delete_and_wide_character_width() -> None:
    parser = SimpleAnsiParser(columns=20, rows=5)
    parser.feed("abcdef\x1b[3G\x1b[@Z")
    assert parser.lines()[0].startswith("abZcdef")

    parser = SimpleAnsiParser(columns=20, rows=5)
    parser.feed("abcdef\x1b[3G\x1b[P")
    assert parser.lines()[0].startswith("abdef")

    parser = SimpleAnsiParser(columns=20, rows=5)
    parser.feed("a\U0001f600b")
    assert parser.cursor_position() == (0, 4)
