from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum


class BaseDirection(str, Enum):
    AUTO = "auto"
    LTR = "ltr"
    RTL = "rtl"


RTL_CLASSES = {"R", "AL", "AN"}
LTR_CLASSES = {"L", "EN"}


@dataclass(frozen=True)
class PreparedLine:
    logical_text: str
    base_direction: BaseDirection
    contains_rtl: bool


class BidiRenderer:
    """Prepares logical terminal lines for Qt rendering.

    The important rule is that this class never reverses Hebrew text manually.
    Qt's text engine applies shaping and BiDi ordering at display time, while
    copy/paste and selection keep the original logical buffer order.
    """

    def prepare_line(self, logical_text: str) -> PreparedLine:
        contains_rtl = any(unicodedata.bidirectional(char) in RTL_CLASSES for char in logical_text)
        return PreparedLine(
            logical_text=logical_text,
            base_direction=self.base_direction(logical_text),
            contains_rtl=contains_rtl,
        )

    def base_direction(self, text: str) -> BaseDirection:
        for char in text:
            bidi_class = unicodedata.bidirectional(char)
            if bidi_class in RTL_CLASSES:
                return BaseDirection.RTL
            if bidi_class in LTR_CLASSES:
                return BaseDirection.LTR
        return BaseDirection.AUTO
