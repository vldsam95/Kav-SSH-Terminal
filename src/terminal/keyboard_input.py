from __future__ import annotations


def qt_key_event_to_terminal_sequence(
    event,
    application_cursor_keys: bool = False,
) -> str | None:
    from PySide6.QtCore import Qt

    key = event.key()
    modifiers = event.modifiers()

    if modifiers & Qt.KeyboardModifier.ControlModifier:
        if key == Qt.Key.Key_C:
            return "\x03"
        if key == Qt.Key.Key_D:
            return "\x04"
        if key == Qt.Key.Key_L:
            return "\x0c"

    if application_cursor_keys:
        cursor_sequences = {
            Qt.Key.Key_Up: "\x1bOA",
            Qt.Key.Key_Down: "\x1bOB",
            Qt.Key.Key_Right: "\x1bOC",
            Qt.Key.Key_Left: "\x1bOD",
            Qt.Key.Key_Home: "\x1bOH",
            Qt.Key.Key_End: "\x1bOF",
        }
    else:
        cursor_sequences = {
            Qt.Key.Key_Up: "\x1b[A",
            Qt.Key.Key_Down: "\x1b[B",
            Qt.Key.Key_Right: "\x1b[C",
            Qt.Key.Key_Left: "\x1b[D",
            Qt.Key.Key_Home: "\x1b[H",
            Qt.Key.Key_End: "\x1b[F",
        }

    special = {
        Qt.Key.Key_Return: "\r",
        Qt.Key.Key_Enter: "\r",
        Qt.Key.Key_Backspace: "\x7f",
        Qt.Key.Key_Tab: "\t",
        Qt.Key.Key_Escape: "\x1b",
        Qt.Key.Key_Delete: "\x1b[3~",
        Qt.Key.Key_PageUp: "\x1b[5~",
        Qt.Key.Key_PageDown: "\x1b[6~",
        **cursor_sequences,
    }
    if key in special:
        return special[key]

    text = event.text()
    if text:
        return text
    return None
