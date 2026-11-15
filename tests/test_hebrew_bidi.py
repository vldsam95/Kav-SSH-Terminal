from __future__ import annotations

from terminal.ansi_parser import strip_ansi
from terminal.bidi_renderer import BaseDirection, BidiRenderer
from terminal.terminal_buffer import TerminalBuffer


def test_hebrew_is_kept_in_logical_order() -> None:
    buffer = TerminalBuffer(columns=120, rows=20, backend="simple")
    buffer.feed('echo "שלום עולם"\n')

    text = buffer.logical_text()

    assert 'echo "שלום עולם"' in text
    assert "םלוע םולש" not in text


def test_mixed_hebrew_english_numbers_are_not_manually_reversed() -> None:
    line = 'echo "בדיקה בעברית עם English 123"'
    prepared = BidiRenderer().prepare_line(line)

    assert prepared.logical_text == line
    assert prepared.contains_rtl is True
    assert "321 hsilgnE" not in prepared.logical_text


def test_first_strong_direction_detection() -> None:
    renderer = BidiRenderer()

    assert renderer.base_direction("שלום world") == BaseDirection.RTL
    assert renderer.base_direction("abc שלום def") == BaseDirection.LTR


def test_ansi_sequences_are_not_part_of_logical_text() -> None:
    buffer = TerminalBuffer(columns=120, rows=20, backend="simple")
    buffer.feed('\x1b[32mקובץ /var/www/html/index.html עודכן\x1b[0m\n')

    assert "קובץ /var/www/html/index.html עודכן" in buffer.logical_text()
    assert "\x1b[" not in strip_ansi(buffer.logical_text())


def test_default_backend_must_preserve_hebrew_unicode() -> None:
    buffer = TerminalBuffer(columns=120, rows=20)
    buffer.feed("שלום עולם\n")

    assert "שלום עולם" in buffer.logical_text()
    assert "????" not in buffer.logical_text()


def test_command_line_repaint_replaces_current_line() -> None:
    buffer = TerminalBuffer(columns=120, rows=20, backend="simple")
    buffer.feed("root# first")
    buffer.feed("\r\x1b[Kroot# second")

    assert buffer.lines()[-1] == "root# second"
    assert "root# first" not in buffer.logical_text()


def test_pyte_backend_repaints_shell_history_line() -> None:
    buffer = TerminalBuffer(columns=120, rows=20, backend="pyte")
    buffer.feed("root# first")
    buffer.feed("\r\x1b[Kroot# second")

    assert buffer.lines()[0] == "root# second"
    assert "root# first" not in buffer.logical_text()


def test_cursor_position_tracks_editing_controls() -> None:
    buffer = TerminalBuffer(columns=120, rows=20, backend="simple")
    buffer.feed("abc")
    assert buffer.cursor_position() == (0, 3)

    buffer.feed("\b\x1b[1G")
    assert buffer.cursor_position() == (0, 0)


def test_simple_backend_rewrites_previous_line_on_cursor_up() -> None:
    buffer = TerminalBuffer(columns=120, rows=20, backend="simple")
    buffer.feed("root# long command that wrapped")
    buffer.feed("\n")
    buffer.feed("root# next")

    buffer.feed("\x1b[A\r\x1b[Kroot# shorter")

    assert buffer.lines()[0] == "root# shorter"
    assert buffer.lines()[1] == "root# next"
