from __future__ import annotations

from terminal.terminal_buffer import TerminalBuffer


def test_simple_backend_preserves_ansi_16_color_spans() -> None:
    buffer = TerminalBuffer(columns=80, rows=10, backend="simple")
    buffer.feed("\x1b[31mred\x1b[0m plain")

    line = buffer.styled_lines()[0]

    assert line.text == "red plain"
    assert line.spans[0].text == "red"
    assert line.spans[0].style.foreground == "#ff5c57"
    assert line.spans[1].text == " plain"
    assert line.spans[1].style.foreground is None


def test_simple_backend_preserves_ansi_256_and_truecolor() -> None:
    buffer = TerminalBuffer(columns=80, rows=10, backend="simple")
    buffer.feed("\x1b[38;5;45midx\x1b[0m \x1b[48;2;10;20;30mbg\x1b[0m")

    spans = buffer.styled_lines()[0].spans

    assert spans[0].text == "idx"
    assert spans[0].style.foreground == "#00d7ff"
    assert spans[2].text == "bg"
    assert spans[2].style.background == "#0a141e"


def test_pyte_backend_exposes_color_spans() -> None:
    buffer = TerminalBuffer(columns=80, rows=10, backend="pyte")
    buffer.feed("\x1b[32mok\x1b[0m")

    line = buffer.styled_lines()[0]

    assert line.text == "ok"
    assert line.spans[0].text == "ok"
    assert line.spans[0].style.foreground == "#5af78e"
