from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from wcwidth import wcwidth

from terminal.style import CellStyle, StyledLine, ansi_256_color, rgb_color, styled_line_from_cells

CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
OSC_RE = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)")
CSI_PARTS_RE = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")


def strip_ansi(text: str) -> str:
    text = OSC_RE.sub("", text)
    return CSI_RE.sub("", text)


@dataclass
class SimpleAnsiParser:
    columns: int = 100
    rows: int = 30
    scrollback: int = 5000
    _lines: list[list[str]] = field(default_factory=lambda: [[]])
    _styles: list[list[CellStyle]] = field(default_factory=lambda: [[]])
    _current_style: CellStyle = field(default_factory=CellStyle)
    _cursor_line: int = 0
    _cursor_col: int = 0
    _saved_cursor: tuple[int, int] = (0, 0)
    _scroll_top: int = 0
    _scroll_bottom: int | None = None

    def feed(self, text: str) -> None:
        index = 0
        while index < len(text):
            char = text[index]
            if char == "\x1b":
                if index + 1 < len(text) and text[index + 1] in ("7", "8"):
                    if text[index + 1] == "7":
                        self._saved_cursor = (self._cursor_line, self._cursor_col)
                    else:
                        self._cursor_line, self._cursor_col = self._saved_cursor
                        self._ensure_line(self._cursor_line)
                    index += 2
                    continue
                match = CSI_RE.match(text, index) or OSC_RE.match(text, index)
                if match:
                    self._handle_escape(match.group(0))
                    index = match.end()
                    continue
            self._handle_char(char)
            index += 1

    def resize(self, columns: int, rows: int) -> None:
        self.columns = max(1, columns)
        self.rows = max(1, rows)
        if self._scroll_bottom is not None:
            self._scroll_bottom = min(self._scroll_bottom, self.rows)

    def lines(self) -> list[str]:
        return ["".join(line).rstrip() for line in self._lines]

    def styled_lines(self) -> list[StyledLine]:
        return [
            styled_line_from_cells(line, self._styles[index])
            for index, line in enumerate(self._lines)
        ]

    def cursor_position(self) -> tuple[int, int]:
        return self._cursor_line, self._cursor_col

    def _handle_escape(self, sequence: str) -> None:
        match = CSI_PARTS_RE.fullmatch(sequence)
        if not match:
            return
        raw_params, _intermediate, final = match.groups()
        params = self._numeric_params(raw_params)

        if final == "m":
            self._handle_sgr(raw_params)
        elif final == "K":
            current = self._current_line()
            current_styles = self._current_styles()
            mode = params[0] if params else 0
            if mode == 1:
                self._blank_line_range(
                    self._cursor_line,
                    0,
                    min(self._cursor_col + 1, len(current)),
                )
            elif mode == 2:
                current.clear()
                current_styles.clear()
                self._cursor_col = 0
            else:
                del current[self._cursor_col :]
                del current_styles[self._cursor_col :]
        elif final == "J":
            mode = params[0] if params else 0
            if mode == 0:
                current = self._current_line()
                self._blank_line_range(self._cursor_line, self._cursor_col, len(current))
                for line_index in range(self._cursor_line + 1, len(self._lines)):
                    self._lines[line_index].clear()
                    self._styles[line_index].clear()
            elif mode == 1:
                for line_index in range(0, self._cursor_line):
                    self._lines[line_index].clear()
                    self._styles[line_index].clear()
                self._blank_line_range(self._cursor_line, 0, self._cursor_col + 1)
            elif mode in (2, 3):
                self._lines = [[]]
                self._styles = [[]]
                self._cursor_line = 0
                self._cursor_col = 0
        elif final == "@":
            self._insert_chars(params[0] if params else 1)
        elif final == "P":
            self._delete_chars(params[0] if params else 1)
        elif final == "X":
            self._erase_chars(params[0] if params else 1)
        elif final == "L":
            self._insert_lines(params[0] if params else 1)
        elif final == "M":
            self._delete_lines(params[0] if params else 1)
        elif final == "A":
            amount = params[0] if params else 1
            self._cursor_line = max(0, self._cursor_line - amount)
        elif final == "B":
            amount = params[0] if params else 1
            self._ensure_line(self._cursor_line + amount)
            self._cursor_line += amount
        elif final == "G":
            column = params[0] if params else 1
            self._cursor_col = max(0, column - 1)
        elif final == "C":
            amount = params[0] if params else 1
            self._cursor_col = min(self.columns - 1, self._cursor_col + amount)
        elif final == "D":
            amount = params[0] if params else 1
            self._cursor_col = max(0, self._cursor_col - amount)
        elif final in ("H", "f"):
            row = params[0] if params else 1
            column = params[1] if len(params) > 1 else 1
            self._cursor_line = max(0, row - 1)
            self._ensure_line(self._cursor_line)
            self._cursor_col = max(0, column - 1)
        elif final == "r":
            top = (params[0] - 1) if params else 0
            bottom = params[1] if len(params) > 1 else self.rows
            if 0 <= top < bottom <= self.rows:
                self._scroll_top = top
                self._scroll_bottom = bottom
                self._cursor_line = top
                self._cursor_col = 0
            else:
                self._scroll_top = 0
                self._scroll_bottom = None
        elif final == "s":
            self._saved_cursor = (self._cursor_line, self._cursor_col)
        elif final == "u":
            self._cursor_line, self._cursor_col = self._saved_cursor
            self._ensure_line(self._cursor_line)

    @staticmethod
    def _numeric_params(raw_params: str) -> list[int]:
        if not raw_params or raw_params.startswith("?"):
            return []
        values: list[int] = []
        for part in raw_params.split(";"):
            if not part:
                values.append(1)
                continue
            try:
                values.append(int(part))
            except ValueError:
                values.append(1)
        return values

    def _handle_sgr(self, raw_params: str) -> None:
        params = self._sgr_params(raw_params)
        index = 0
        while index < len(params):
            code = params[index]
            if code == 0:
                self._current_style = CellStyle()
            elif code == 1:
                self._current_style = replace(self._current_style, bold=True)
            elif code == 3:
                self._current_style = replace(self._current_style, italic=True)
            elif code == 4:
                self._current_style = replace(self._current_style, underline=True)
            elif code == 7:
                self._current_style = replace(self._current_style, reverse=True)
            elif code == 9:
                self._current_style = replace(self._current_style, strikethrough=True)
            elif code == 22:
                self._current_style = replace(self._current_style, bold=False)
            elif code == 23:
                self._current_style = replace(self._current_style, italic=False)
            elif code == 24:
                self._current_style = replace(self._current_style, underline=False)
            elif code == 27:
                self._current_style = replace(self._current_style, reverse=False)
            elif code == 29:
                self._current_style = replace(self._current_style, strikethrough=False)
            elif 30 <= code <= 37:
                self._current_style = replace(
                    self._current_style,
                    foreground=ansi_256_color(code - 30),
                )
            elif code == 39:
                self._current_style = replace(self._current_style, foreground=None)
            elif 40 <= code <= 47:
                self._current_style = replace(
                    self._current_style,
                    background=ansi_256_color(code - 40),
                )
            elif code == 49:
                self._current_style = replace(self._current_style, background=None)
            elif 90 <= code <= 97:
                self._current_style = replace(
                    self._current_style,
                    foreground=ansi_256_color(code - 90 + 8),
                )
            elif 100 <= code <= 107:
                self._current_style = replace(
                    self._current_style,
                    background=ansi_256_color(code - 100 + 8),
                )
            elif code in (38, 48):
                color, consumed = self._extended_color(params, index + 1)
                if color is not None:
                    field_name = "foreground" if code == 38 else "background"
                    self._current_style = replace(self._current_style, **{field_name: color})
                index += consumed
            index += 1

    @staticmethod
    def _sgr_params(raw_params: str) -> list[int]:
        if not raw_params:
            return [0]
        params: list[int] = []
        for part in raw_params.replace(":", ";").split(";"):
            if part == "":
                params.append(0)
                continue
            try:
                params.append(int(part))
            except ValueError:
                params.append(0)
        return params

    @staticmethod
    def _extended_color(params: list[int], index: int) -> tuple[str | None, int]:
        if index >= len(params):
            return None, 0
        mode = params[index]
        if mode == 5 and index + 1 < len(params):
            return ansi_256_color(params[index + 1]), 2
        if mode == 2 and index + 3 < len(params):
            return rgb_color(params[index + 1], params[index + 2], params[index + 3]), 4
        return None, 1

    def _handle_char(self, char: str) -> None:
        if char == "\r":
            self._cursor_col = 0
            return
        if char == "\n":
            self._newline()
            return
        if char == "\b":
            self._cursor_col = max(0, self._cursor_col - 1)
            return
        if char == "\t":
            spaces = 8 - (self._cursor_col % 8)
            for _ in range(spaces):
                self._put_char(" ")
            return
        if char < " " and char not in ("\u200e", "\u200f"):
            return
        self._put_char(char)

    def _put_char(self, char: str) -> None:
        width = self._terminal_width(char)
        if width == 0:
            if self._cursor_col > 0:
                self._ensure_line(self._cursor_line)
                current = self._current_line()
                if self._cursor_col - 1 < len(current):
                    current[self._cursor_col - 1] += char
            return

        self._ensure_line(self._cursor_line)
        current = self._current_line()
        current_styles = self._current_styles()
        required_cells = self._cursor_col + width
        if required_cells > len(current):
            current.extend(" " for _ in range(required_cells - len(current)))
            current_styles.extend(
                self._current_style for _ in range(required_cells - len(current_styles))
            )
        current[self._cursor_col] = char
        current_styles[self._cursor_col] = self._current_style
        for offset in range(1, width):
            current[self._cursor_col + offset] = " "
            current_styles[self._cursor_col + offset] = self._current_style
        self._cursor_col += width
        if self._cursor_col >= self.columns:
            self._newline()

    def _newline(self) -> None:
        bottom = self._effective_scroll_bottom()
        if self._scroll_bottom is not None and self._scroll_top <= self._cursor_line < bottom:
            if self._cursor_line == bottom - 1:
                self._scroll_up_region(1)
            else:
                self._cursor_line += 1
                self._ensure_line(self._cursor_line)
            self._cursor_col = 0
            return

        self._cursor_line += 1
        self._ensure_line(self._cursor_line)
        self._cursor_col = 0
        overflow = len(self._lines) - self.scrollback
        if overflow > 0:
            del self._lines[:overflow]
            del self._styles[:overflow]
            self._cursor_line = max(0, self._cursor_line - overflow)

    def _ensure_line(self, line_index: int) -> None:
        while line_index >= len(self._lines):
            self._lines.append([])
            self._styles.append([])

    def _current_line(self) -> list[str]:
        self._ensure_line(self._cursor_line)
        return self._lines[self._cursor_line]

    def _current_styles(self) -> list[CellStyle]:
        self._ensure_line(self._cursor_line)
        return self._styles[self._cursor_line]

    def _blank_line_range(self, line_index: int, start: int, end: int) -> None:
        if end <= start:
            return
        self._ensure_line(line_index)
        line = self._lines[line_index]
        styles = self._styles[line_index]
        if end > len(line):
            line.extend(" " for _ in range(end - len(line)))
            styles.extend(CellStyle() for _ in range(end - len(styles)))
        for index in range(start, end):
            line[index] = " "
            styles[index] = CellStyle()

    def _insert_chars(self, count: int) -> None:
        count = max(1, count)
        current = self._current_line()
        current_styles = self._current_styles()
        self._ensure_cells(self._cursor_line, self.columns)
        limit = self.columns
        blanks = [" "] * count
        blank_styles = [CellStyle()] * count
        current[self._cursor_col : self._cursor_col] = blanks
        current_styles[self._cursor_col : self._cursor_col] = blank_styles
        del current[limit:]
        del current_styles[limit:]

    def _delete_chars(self, count: int) -> None:
        count = max(1, count)
        current = self._current_line()
        current_styles = self._current_styles()
        self._ensure_cells(self._cursor_line, self.columns)
        del current[self._cursor_col : self._cursor_col + count]
        del current_styles[self._cursor_col : self._cursor_col + count]
        current.extend(" " for _ in range(count))
        current_styles.extend(CellStyle() for _ in range(count))
        del current[self.columns :]
        del current_styles[self.columns :]

    def _erase_chars(self, count: int) -> None:
        self._blank_line_range(self._cursor_line, self._cursor_col, self._cursor_col + max(1, count))

    def _insert_lines(self, count: int) -> None:
        if not self._cursor_in_scroll_region():
            return
        count = max(1, count)
        bottom = self._effective_scroll_bottom()
        self._ensure_line(bottom - 1)
        for _ in range(count):
            self._lines.insert(self._cursor_line, [])
            self._styles.insert(self._cursor_line, [])
            del self._lines[bottom]
            del self._styles[bottom]

    def _delete_lines(self, count: int) -> None:
        if not self._cursor_in_scroll_region():
            return
        count = max(1, count)
        bottom = self._effective_scroll_bottom()
        self._ensure_line(bottom - 1)
        for _ in range(count):
            del self._lines[self._cursor_line]
            del self._styles[self._cursor_line]
            self._lines.insert(bottom - 1, [])
            self._styles.insert(bottom - 1, [])

    def _scroll_up_region(self, count: int) -> None:
        bottom = self._effective_scroll_bottom()
        self._ensure_line(bottom - 1)
        for _ in range(max(1, count)):
            del self._lines[self._scroll_top]
            del self._styles[self._scroll_top]
            self._lines.insert(bottom - 1, [])
            self._styles.insert(bottom - 1, [])

    def _cursor_in_scroll_region(self) -> bool:
        return self._scroll_top <= self._cursor_line < self._effective_scroll_bottom()

    def _effective_scroll_bottom(self) -> int:
        return self._scroll_bottom or self.rows

    def _ensure_cells(self, line_index: int, count: int) -> None:
        self._ensure_line(line_index)
        line = self._lines[line_index]
        styles = self._styles[line_index]
        if len(line) < count:
            line.extend(" " for _ in range(count - len(line)))
            styles.extend(CellStyle() for _ in range(count - len(styles)))

    @staticmethod
    def _terminal_width(char: str) -> int:
        width = wcwidth(char)
        if width < 0:
            return 1
        return min(2, width)
