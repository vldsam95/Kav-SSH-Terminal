from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Scrollback:
    limit: int = 5000
    _items: deque[str] = field(init=False)

    def __post_init__(self) -> None:
        self._items = deque(maxlen=self.limit)

    def extend(self, lines: Iterable[str]) -> None:
        self._items.extend(lines)

    def append(self, line: str) -> None:
        self._items.append(line)

    def lines(self) -> list[str]:
        return list(self._items)
