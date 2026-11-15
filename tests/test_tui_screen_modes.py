from __future__ import annotations

from terminal.terminal_buffer import TerminalBuffer


def test_pyte_alternate_screen_does_not_overlay_shell_history() -> None:
    buffer = TerminalBuffer(columns=20, rows=5, backend="pyte")
    buffer.feed("shell prompt\r\n")

    buffer.feed("\x1b[?1049h\x1b[H/menu\r\nitem")

    assert "shell prompt" not in buffer.logical_text()
    assert "/menu" in buffer.logical_text()

    buffer.feed("\x1b[?1049l")

    assert "shell prompt" in buffer.logical_text()
    assert "/menu" not in buffer.logical_text()


def test_pyte_alternate_screen_handles_split_private_mode_sequence() -> None:
    buffer = TerminalBuffer(columns=20, rows=5, backend="pyte")
    buffer.feed("shell prompt\r\n")
    buffer.feed("\x1b[?104")
    buffer.feed("9h\x1b[Hmenu")

    assert "shell prompt" not in buffer.logical_text()
    assert "menu" in buffer.logical_text()


def test_simple_backend_erase_display_from_cursor_cleans_popup_area() -> None:
    buffer = TerminalBuffer(columns=20, rows=5, backend="simple")
    buffer.feed("prompt\r\n/menu\r\n/model\r\n/review")
    buffer.feed("\x1b[2;1H\x1b[J")

    assert buffer.lines()[0] == "prompt"
    assert all(line == "" for line in buffer.lines()[1:])
