from __future__ import annotations

import re
from dataclasses import dataclass

from terminal.ansi_parser import SimpleAnsiParser
from terminal.style import CellStyle, StyledLine, normalize_color, styled_line_from_cells

PRIVATE_MODE_RE = re.compile(r"\x1b\[\?([0-9;]+)([hl])")
PRIVATE_MODE_PREFIX_RE = re.compile(r"^\x1b(?:\[\??[0-9;]*)?$")


@dataclass
class TerminalSize:
    columns: int = 100
    rows: int = 30


class TerminalBuffer:
    def __init__(
        self,
        columns: int = 100,
        rows: int = 30,
        scrollback: int = 5000,
        backend: str = "simple",
    ) -> None:
        self.size = TerminalSize(columns=columns, rows=rows)
        self.scrollback = scrollback
        self._backend_name = "simple"
        self._pyte_module = None
        self._pyte_screen_cls = None
        self._main_pyte_screen = None
        self._main_pyte_stream = None
        self._alternate_pyte_screen = None
        self._alternate_pyte_stream = None
        self._pyte_screen = None
        self._pyte_stream = None
        self._using_alternate_screen = False
        self._pending_pyte_text = ""
        self.application_cursor_keys = False
        self.bracketed_paste = False
        self.mouse_tracking = "off"
        self.mouse_sgr = False
        self._simple = SimpleAnsiParser(columns=columns, rows=rows, scrollback=scrollback)

        if backend == "pyte":
            self._try_enable_pyte(backend_required=True)

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def is_screen_backend(self) -> bool:
        return self._pyte_screen is not None

    def feed(self, data: bytes | str) -> None:
        text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
        if self._pyte_stream is not None:
            self._feed_pyte(text)
        else:
            self._simple.feed(text)

    def resize(self, columns: int, rows: int) -> None:
        columns = max(1, columns)
        rows = max(1, rows)
        self.size = TerminalSize(columns=columns, rows=rows)
        for screen in (self._main_pyte_screen, self._alternate_pyte_screen):
            if screen is not None:
                screen.resize(rows, columns)
        self._simple.resize(columns, rows)

    def lines(self) -> list[str]:
        if self._pyte_screen is not None:
            return [line.rstrip() for line in self._pyte_screen.display]
        return self._simple.lines()

    def styled_lines(self) -> list[StyledLine]:
        if self._pyte_screen is not None:
            return self._pyte_styled_lines()
        return self._simple.styled_lines()

    def cursor_position(self) -> tuple[int, int]:
        if self._pyte_screen is not None:
            cursor = self._pyte_screen.cursor
            return cursor.y, cursor.x
        return self._simple.cursor_position()

    def visible_lines(self) -> list[str]:
        return self.lines()[-self.size.rows :]

    def logical_text(self) -> str:
        return "\n".join(self.lines())

    def _try_enable_pyte(self, backend_required: bool) -> None:
        try:
            import pyte
        except ImportError as exc:
            if backend_required:
                raise RuntimeError("pyte backend requested but pyte is not installed.") from exc
            return

        try:
            screen_cls = getattr(pyte, "HistoryScreen", pyte.Screen)
            probe_screen = self._new_pyte_screen(pyte, screen_cls)
            probe_stream = pyte.Stream(probe_screen)
            probe_stream.feed("שלום")
            if "שלום" not in "\n".join(line.rstrip() for line in probe_screen.display):
                if backend_required:
                    raise RuntimeError("pyte backend does not preserve Hebrew Unicode text.")
                return

            self._pyte_module = pyte
            self._pyte_screen_cls = screen_cls
            self._main_pyte_screen = self._new_pyte_screen(pyte, screen_cls)
            self._main_pyte_stream = pyte.Stream(self._main_pyte_screen)
            self._pyte_screen = self._main_pyte_screen
            self._pyte_stream = self._main_pyte_stream
            self._backend_name = "pyte"
        except Exception as exc:
            if backend_required:
                raise RuntimeError("Failed to initialize pyte terminal backend.") from exc
            self._pyte_module = None
            self._pyte_screen_cls = None
            self._main_pyte_screen = None
            self._main_pyte_stream = None
            self._alternate_pyte_screen = None
            self._alternate_pyte_stream = None
            self._pyte_screen = None
            self._pyte_stream = None

    def _new_pyte_screen(self, pyte_module, screen_cls):
        try:
            return screen_cls(
                self.size.columns,
                self.size.rows,
                history=self.scrollback,
            )
        except TypeError:
            return pyte_module.Screen(self.size.columns, self.size.rows)

    def _feed_pyte(self, text: str) -> None:
        assert self._pyte_stream is not None
        if self._pending_pyte_text:
            text = self._pending_pyte_text + text
            self._pending_pyte_text = ""

        segment_start = 0
        index = 0
        while index < len(text):
            if text[index] != "\x1b":
                index += 1
                continue

            match = PRIVATE_MODE_RE.match(text, index)
            if match:
                self._pyte_stream.feed(text[segment_start:index])
                self._handle_private_mode(match.group(1), match.group(2))
                index = match.end()
                segment_start = index
                continue

            remainder = text[index:]
            if PRIVATE_MODE_PREFIX_RE.fullmatch(remainder):
                self._pyte_stream.feed(text[segment_start:index])
                self._pending_pyte_text = remainder
                return

            index += 1

        self._pyte_stream.feed(text[segment_start:])

    def _handle_private_mode(self, raw_modes: str, final: str) -> None:
        enabled = final == "h"
        for raw_mode in raw_modes.split(";"):
            try:
                mode = int(raw_mode)
            except ValueError:
                continue
            if mode in (47, 1047, 1049):
                if enabled:
                    self._enter_alternate_screen(save_cursor=mode == 1049)
                else:
                    self._exit_alternate_screen(restore_cursor=mode == 1049)
            elif mode == 1:
                self.application_cursor_keys = enabled
            elif mode == 2004:
                self.bracketed_paste = enabled
            elif mode in (1000, 1002, 1003):
                if enabled:
                    self.mouse_tracking = {
                        1000: "click",
                        1002: "button",
                        1003: "any",
                    }[mode]
                elif self.mouse_tracking == {
                    1000: "click",
                    1002: "button",
                    1003: "any",
                }[mode]:
                    self.mouse_tracking = "off"
            elif mode == 1006:
                self.mouse_sgr = enabled
            elif mode == 1048:
                if self._pyte_screen is None:
                    continue
                if enabled:
                    self._pyte_screen.save_cursor()
                else:
                    self._pyte_screen.restore_cursor()

    def _enter_alternate_screen(self, save_cursor: bool) -> None:
        if self._pyte_module is None:
            return
        if save_cursor and self._pyte_screen is not None:
            self._pyte_screen.save_cursor()

        self._alternate_pyte_screen = self._pyte_module.Screen(
            self.size.columns,
            self.size.rows,
        )
        self._alternate_pyte_stream = self._pyte_module.Stream(self._alternate_pyte_screen)
        self._pyte_screen = self._alternate_pyte_screen
        self._pyte_stream = self._alternate_pyte_stream
        self._using_alternate_screen = True

    def _exit_alternate_screen(self, restore_cursor: bool) -> None:
        if self._main_pyte_screen is None or self._main_pyte_stream is None:
            return
        self._alternate_pyte_screen = None
        self._alternate_pyte_stream = None
        self._pyte_screen = self._main_pyte_screen
        self._pyte_stream = self._main_pyte_stream
        self._using_alternate_screen = False
        if restore_cursor:
            self._pyte_screen.restore_cursor()

    def _pyte_styled_lines(self) -> list[StyledLine]:
        assert self._pyte_screen is not None
        styled_lines: list[StyledLine] = []
        for row in range(self.size.rows):
            row_buffer = self._pyte_screen.buffer[row]
            chars = []
            styles = []
            for column in range(self.size.columns):
                cell = row_buffer[column]
                chars.append(cell.data)
                styles.append(self._style_from_pyte_cell(cell))
            styled_lines.append(styled_line_from_cells(chars, styles))
        return styled_lines

    @staticmethod
    def _style_from_pyte_cell(cell) -> CellStyle:
        return CellStyle(
            foreground=normalize_color(cell.fg),
            background=normalize_color(cell.bg),
            bold=bool(cell.bold),
            italic=bool(cell.italics),
            underline=bool(cell.underscore),
            strikethrough=bool(cell.strikethrough),
            reverse=bool(cell.reverse),
        )
