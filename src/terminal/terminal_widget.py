from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPalette,
    QPen,
    QTextOption,
)
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QMenu

from app.settings import TerminalSettings
from terminal.bidi_renderer import BaseDirection, BidiRenderer
from terminal.font_selection import resolve_terminal_font_family
from terminal.keyboard_input import qt_key_event_to_terminal_sequence
from terminal.selection import SelectionRange
from terminal.style import CellStyle, StyledLine, normalize_color
from terminal.terminal_buffer import TerminalBuffer


class TerminalWidget(QAbstractScrollArea):
    input_requested = Signal(str)
    terminal_resized = Signal(int, int)

    def __init__(self, settings: TerminalSettings | None = None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings or TerminalSettings()
        self.buffer = TerminalBuffer(
            columns=self.settings.columns,
            rows=self.settings.rows,
            scrollback=self.settings.scrollback_lines,
            backend=self.settings.parser_backend,
        )
        self.renderer = BidiRenderer()
        self.selection: SelectionRange | None = None
        self._drag_anchor: tuple[int, int] | None = None
        self._char_width = 8.0
        self._line_height = 18.0
        self._padding = 8
        self._terminal_font = QFont()
        self._pending_feed: list[str] = []
        self._feed_timer = QTimer(self)
        self._feed_timer.setInterval(16)
        self._feed_timer.setSingleShot(True)
        self._feed_timer.timeout.connect(self._flush_pending_feed)
        self._mouse_button_code: int | None = None
        self._cursor_visible = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(530)
        self._cursor_timer.timeout.connect(self._blink_cursor)
        self._cursor_timer.start()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.apply_settings(self.settings)

    def apply_settings(self, settings: TerminalSettings) -> None:
        self.settings = settings
        family = resolve_terminal_font_family(settings.font_family)
        font = QFont(family, settings.font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self._terminal_font = font
        self.setFont(font)
        self.viewport().setFont(font)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(settings.background))
        palette.setColor(QPalette.ColorRole.Text, QColor(settings.foreground))
        self.setPalette(palette)
        self._update_metrics()
        self._sync_scrollbar()
        self.viewport().update()

    def feed(self, data: bytes | str) -> None:
        text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
        if not text:
            return
        self._pending_feed.append(text)
        if not self._feed_timer.isActive():
            self._feed_timer.start()

    def _flush_pending_feed(self) -> None:
        if not self._pending_feed:
            return

        top_before = self.verticalScrollBar().value()
        cursor_before = self.buffer.cursor_position()
        before = self._visible_text_snapshot(top_before)
        text = "".join(self._pending_feed)
        self._pending_feed.clear()

        self.buffer.feed(text)
        self._sync_scrollbar(stick_to_bottom=True)
        self._cursor_visible = True
        top_after = self.verticalScrollBar().value()
        cursor_after = self.buffer.cursor_position()
        after = self._visible_text_snapshot(top_after)
        if top_before != top_after or len(before) != len(after):
            self.viewport().update()
            return
        self._update_changed_rows(before, after, top_after, cursor_before, cursor_after)

    def selected_text(self) -> str:
        if self.selection is None:
            return ""
        selection = self.selection.normalized()
        lines = self.buffer.lines()
        selected_lines: list[str] = []
        for line_index in range(selection.start_line, selection.end_line + 1):
            if line_index >= len(lines):
                break
            line = lines[line_index]
            span = selection.span_for_line(line_index, len(line))
            if span is None:
                selected_lines.append("")
                continue
            start, end = span
            selected_lines.append(line[start:end])
        return "\n".join(selected_lines)

    def copy(self) -> None:
        text = self.selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def paste(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            if self.buffer.bracketed_paste:
                text = f"\x1b[200~{text}\x1b[201~"
            self.input_requested.emit(text)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override.
        super().resizeEvent(event)
        self._update_metrics()
        columns = max(20, int((self.viewport().width() - self._padding * 2) / self._char_width))
        rows = max(5, int((self.viewport().height() - self._padding * 2) / self._line_height))
        if columns != self.buffer.size.columns or rows != self.buffer.size.rows:
            self.buffer.resize(columns, rows)
            self.terminal_resized.emit(columns, rows)
        self._sync_scrollbar()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override.
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), QColor(self.settings.background))
        painter.setFont(self._terminal_font)
        self._paint_terminal_texture(painter, event.rect())

        styled_lines = self.buffer.styled_lines()
        lines = [line.text for line in styled_lines]
        visible_rows = self._visible_row_count()
        top = self.verticalScrollBar().value()
        bottom = min(len(lines), top + visible_rows)

        first_offset = max(0, int((event.rect().top() - self._padding) / self._line_height))
        last_offset = min(
            bottom - top,
            int((event.rect().bottom() - self._padding) / self._line_height) + 1,
        )

        y = self._padding + first_offset * self._line_height
        for line_index in range(top + first_offset, top + last_offset):
            logical_line = lines[line_index]
            line_rect = QRectF(
                self._padding,
                y,
                max(1, self.viewport().width() - self._padding * 2),
                self._line_height,
            )
            prepared = self.renderer.prepare_line(logical_line)
            direction = self._qt_direction(prepared.base_direction)
            self._paint_styled_backgrounds(painter, styled_lines[line_index], line_rect)
            if self.selection:
                self._paint_selection_for_line(painter, line_index, logical_line, line_rect)
            self._paint_styled_text(
                painter,
                styled_lines[line_index],
                line_rect,
                direction,
            )
            y += self._line_height
        self._paint_cursor(painter, top, bottom)

    def _paint_styled_backgrounds(
        self,
        painter: QPainter,
        styled_line: StyledLine,
        line_rect: QRectF,
    ) -> None:
        for span in styled_line.spans:
            _foreground, background = self._resolved_style_colors(span.style)
            if background is None:
                continue
            span_rect = self._span_rect(line_rect, span.start, span.end)
            painter.fillRect(span_rect, QColor(background))

    def _paint_styled_text(
        self,
        painter: QPainter,
        styled_line: StyledLine,
        line_rect: QRectF,
        direction: Qt.LayoutDirection,
    ) -> None:
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.NoWrap)
        option.setTextDirection(direction)

        base_font = self._terminal_font
        for span in styled_line.spans:
            foreground, _background = self._resolved_style_colors(span.style)
            span_font = QFont(base_font)
            span_font.setBold(span.style.bold)
            span_font.setItalic(span.style.italic)
            span_font.setUnderline(span.style.underline)
            span_font.setStrikeOut(span.style.strikethrough)
            painter.setFont(span_font)
            painter.setPen(QColor(foreground))
            painter.drawText(self._span_rect(line_rect, span.start, span.end), span.text, option)
        painter.setFont(base_font)

    def _span_rect(self, line_rect: QRectF, start: int, end: int) -> QRectF:
        return QRectF(
            line_rect.left() + start * self._char_width,
            line_rect.top(),
            max(1.0, (end - start) * self._char_width),
            line_rect.height(),
        )

    def _resolved_style_colors(self, style: CellStyle) -> tuple[str, str | None]:
        foreground = normalize_color(style.foreground) or self.settings.foreground
        background = normalize_color(style.background)
        if style.reverse:
            foreground, background = background or self.settings.background, foreground
        return foreground, background

    def _paint_selection_for_line(
        self,
        painter: QPainter,
        line_index: int,
        logical_line: str,
        line_rect: QRectF,
    ) -> None:
        if self.selection is None:
            return
        span = self.selection.span_for_line(line_index, len(logical_line))
        if span is None:
            return
        start, end = span
        x = line_rect.left() + start * self._char_width
        width = max(1.0, (end - start) * self._char_width)
        selection_rect = QRectF(x, line_rect.top(), width, line_rect.height())
        painter.fillRect(selection_rect, QColor(self.settings.selection))

    def _paint_terminal_texture(self, painter: QPainter, rect: QRectF) -> None:
        line_color = QColor("#0b2427")
        line_color.setAlpha(72)
        painter.setPen(QPen(line_color, 1))
        step = max(4, int(self._line_height * 2))
        start_y = int(rect.top()) - (int(rect.top()) % step)
        for y in range(start_y, int(rect.bottom()) + step, step):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

    def _paint_cursor(self, painter: QPainter, top: int, bottom: int) -> None:
        if not self._cursor_visible:
            return
        cursor_line, cursor_col = self.buffer.cursor_position()
        if cursor_line < top or cursor_line >= bottom:
            return
        x = self._padding + cursor_col * self._char_width
        max_x = self.viewport().width() - self._padding
        if x > max_x:
            return
        y = self._padding + (cursor_line - top) * self._line_height
        cursor_color = QColor(self.settings.cursor)
        cursor_color.setAlpha(190)
        painter.fillRect(QRectF(x, y + 2, self._char_width, self._line_height - 4), cursor_color)

    def _blink_cursor(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self.viewport().update()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override.
        from PySide6.QtCore import Qt

        modifiers = event.modifiers()
        has_copy_paste_modifier = (
            modifiers & Qt.KeyboardModifier.ControlModifier
            and modifiers & Qt.KeyboardModifier.ShiftModifier
        )
        if has_copy_paste_modifier:
            if event.key() == Qt.Key.Key_C:
                self.copy()
                return
            if event.key() == Qt.Key.Key_V:
                self.paste()
                return

        sequence = qt_key_event_to_terminal_sequence(
            event,
            application_cursor_keys=self.buffer.application_cursor_keys,
        )
        if sequence is not None:
            self._cursor_visible = True
            self.input_requested.emit(sequence)
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override.
        if self._should_send_mouse_event(event):
            button_code = self._button_code(event.button())
            if button_code is not None:
                self._mouse_button_code = button_code
                self.input_requested.emit(
                    self._mouse_sequence(event.position().toPoint(), button_code, event, True)
                )
                return
        if event.button() == Qt.MouseButton.LeftButton:
            line, col = self._cell_at(event.position().toPoint())
            self._drag_anchor = (line, col)
            self.selection = SelectionRange(line, col, line, col)
            self.viewport().update()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override.
        if self._should_send_mouse_event(event):
            tracking = self.buffer.mouse_tracking
            if tracking == "any" or (tracking == "button" and self._mouse_button_code is not None):
                base_code = self._mouse_button_code if self._mouse_button_code is not None else 3
                self.input_requested.emit(
                    self._mouse_sequence(event.position().toPoint(), base_code + 32, event, True)
                )
                return
        if self._drag_anchor is not None:
            line, col = self._cell_at(event.position().toPoint())
            self.selection = SelectionRange(
                self._drag_anchor[0],
                self._drag_anchor[1],
                line,
                col,
            )
            self.viewport().update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override.
        if self._should_send_mouse_event(event):
            button_code = self._mouse_button_code if self._mouse_button_code is not None else 3
            self.input_requested.emit(
                self._mouse_sequence(event.position().toPoint(), button_code, event, False)
            )
            self._mouse_button_code = None
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_anchor = None
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt override.
        if self._should_send_mouse_event(event):
            button_code = 64 if event.angleDelta().y() > 0 else 65
            self.input_requested.emit(
                self._mouse_sequence(event.position().toPoint(), button_code, event, True)
            )
            return
        super().wheelEvent(event)

    def _cell_at(self, point: QPoint) -> tuple[int, int]:
        row = max(0, int((point.y() - self._padding) / self._line_height))
        max_line = max(0, len(self.buffer.lines()) - 1)
        line = min(max(0, self.verticalScrollBar().value() + row), max_line)
        col = max(0, int((point.x() - self._padding) / self._char_width))
        return line, col

    def _screen_cell_at(self, point: QPoint) -> tuple[int, int]:
        col = max(
            1,
            min(
                self.buffer.size.columns,
                int((point.x() - self._padding) / self._char_width) + 1,
            ),
        )
        row = max(
            1,
            min(
                self.buffer.size.rows,
                int((point.y() - self._padding) / self._line_height) + 1,
            ),
        )
        return col, row

    def _should_send_mouse_event(self, event) -> bool:
        if self.buffer.mouse_tracking == "off":
            return False
        return not bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

    @staticmethod
    def _button_code(button: Qt.MouseButton) -> int | None:
        if button == Qt.MouseButton.LeftButton:
            return 0
        if button == Qt.MouseButton.MiddleButton:
            return 1
        if button == Qt.MouseButton.RightButton:
            return 2
        return None

    def _mouse_sequence(self, point: QPoint, button_code: int, event, pressed: bool) -> str:
        col, row = self._screen_cell_at(point)
        code = button_code | self._mouse_modifier_code(event.modifiers())
        if self.buffer.mouse_sgr:
            suffix = "M" if pressed else "m"
            return f"\x1b[<{code};{col};{row}{suffix}"
        if col > 223 or row > 223:
            return ""
        if not pressed:
            code = 3 | self._mouse_modifier_code(event.modifiers())
        return "\x1b[M" + chr(32 + code) + chr(32 + col) + chr(32 + row)

    @staticmethod
    def _mouse_modifier_code(modifiers: Qt.KeyboardModifiers) -> int:
        code = 0
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            code |= 4
        if modifiers & Qt.KeyboardModifier.AltModifier:
            code |= 8
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            code |= 16
        return code

    def _show_context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        copy_action = QAction("Copy", self)
        paste_action = QAction("Paste", self)
        copy_action.triggered.connect(self.copy)
        paste_action.triggered.connect(self.paste)
        copy_action.setEnabled(bool(self.selected_text()))
        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.exec(self.viewport().mapToGlobal(point))

    def _qt_direction(self, direction: BaseDirection) -> Qt.LayoutDirection:
        if direction == BaseDirection.RTL:
            return Qt.LayoutDirection.RightToLeft
        if direction == BaseDirection.LTR:
            return Qt.LayoutDirection.LeftToRight
        return Qt.LayoutDirection.LayoutDirectionAuto

    def _update_metrics(self) -> None:
        metrics = QFontMetricsF(self._terminal_font)
        self._char_width = max(
            1.0,
            metrics.horizontalAdvance("0"),
            metrics.horizontalAdvance(" "),
            metrics.averageCharWidth(),
        )
        self._line_height = max(1.0, metrics.height() + 2)

    def _visible_row_count(self) -> int:
        return max(1, int((self.viewport().height() - self._padding * 2) / self._line_height))

    def _sync_scrollbar(self, stick_to_bottom: bool = False) -> None:
        if self.buffer.is_screen_backend:
            self.verticalScrollBar().setRange(0, 0)
            return

        lines = self.buffer.lines()
        visible_rows = self._visible_row_count()
        maximum = max(0, len(lines) - visible_rows)
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 1
        scrollbar.setRange(0, maximum)
        scrollbar.setPageStep(visible_rows)
        if stick_to_bottom and was_at_bottom:
            scrollbar.setValue(maximum)

    def _visible_text_snapshot(self, top: int) -> list[str]:
        lines = self.buffer.lines()
        visible_rows = self._visible_row_count()
        return lines[top : top + visible_rows]

    def _update_changed_rows(
        self,
        before: list[str],
        after: list[str],
        top: int,
        cursor_before: tuple[int, int],
        cursor_after: tuple[int, int],
    ) -> None:
        dirty_rows = {
            index
            for index, (old, new) in enumerate(zip(before, after, strict=False))
            if old != new
        }
        for cursor_line, _cursor_col in (cursor_before, cursor_after):
            row = cursor_line - top
            if 0 <= row < self._visible_row_count():
                dirty_rows.add(row)
        if not dirty_rows:
            return
        visible_rows = self._visible_row_count()
        if len(dirty_rows) > max(4, visible_rows // 2):
            self.viewport().update()
            return
        for row in dirty_rows:
            self.viewport().update(self._row_rect(row))

    def _row_rect(self, visible_row: int) -> QRect:
        y = int(self._padding + visible_row * self._line_height)
        return QRect(
            0,
            max(0, y - 1),
            self.viewport().width(),
            int(self._line_height) + 3,
        )
