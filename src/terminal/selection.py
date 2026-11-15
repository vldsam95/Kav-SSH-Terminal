from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SelectionRange:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def normalized(self) -> SelectionRange:
        start = (self.start_line, self.start_col)
        end = (self.end_line, self.end_col)
        if start <= end:
            return self
        return SelectionRange(self.end_line, self.end_col, self.start_line, self.start_col)

    def contains_line(self, line_index: int) -> bool:
        normalized = self.normalized()
        return normalized.start_line <= line_index <= normalized.end_line

    def span_for_line(self, line_index: int, line_length: int) -> tuple[int, int] | None:
        normalized = self.normalized()
        if not normalized.contains_line(line_index):
            return None
        if normalized.start_line == normalized.end_line:
            start = min(normalized.start_col, line_length)
            end = min(normalized.end_col, line_length)
            return (start, end) if start < end else None
        if line_index == normalized.start_line:
            start = min(normalized.start_col, line_length)
            return (start, line_length) if start < line_length else None
        if line_index == normalized.end_line:
            end = min(normalized.end_col, line_length)
            return (0, end) if end > 0 else None
        return (0, line_length) if line_length > 0 else None
