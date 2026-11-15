from __future__ import annotations

from terminal.selection import SelectionRange


def test_selection_normalizes_reversed_columns() -> None:
    selection = SelectionRange(3, 9, 1, 2).normalized()

    assert selection == SelectionRange(1, 2, 3, 9)


def test_selection_span_for_single_line() -> None:
    selection = SelectionRange(0, 2, 0, 7)

    assert selection.span_for_line(0, 10) == (2, 7)
    assert selection.span_for_line(1, 10) is None


def test_selection_span_for_multiple_lines() -> None:
    selection = SelectionRange(0, 4, 2, 3)

    assert selection.span_for_line(0, 10) == (4, 10)
    assert selection.span_for_line(1, 10) == (0, 10)
    assert selection.span_for_line(2, 10) == (0, 3)
