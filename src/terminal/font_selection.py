from __future__ import annotations

from PySide6.QtGui import QFontDatabase


TERMINAL_FONT_CANDIDATES = (
    "Cascadia Mono",
    "Cascadia Code",
    "Consolas",
    "Courier New",
    "Lucida Console",
    "DejaVu Sans Mono",
    "Noto Sans Mono",
    "Liberation Mono",
    "Miriam Fixed",
)


def resolve_terminal_font_family(preferred: str | None = None) -> str:
    fixed_family = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
    candidates = [preferred or "", *TERMINAL_FONT_CANDIDATES, fixed_family]
    available = set(QFontDatabase.families())
    if not available:
        return preferred or fixed_family

    fixed_candidates = [
        family
        for family in candidates
        if family and family in available and QFontDatabase.isFixedPitch(family)
    ]
    for family in fixed_candidates:
        if _font_supports_hebrew_and_cyrillic(family):
            return family
    for family in fixed_candidates:
        if _font_supports_hebrew(family):
            return family
    if fixed_candidates:
        return fixed_candidates[0]
    return fixed_family


def _font_supports_hebrew_and_cyrillic(family: str) -> bool:
    systems = {
        QFontDatabase.writingSystemName(system)
        for system in QFontDatabase.writingSystems(family)
    }
    return "Hebrew" in systems and "Cyrillic" in systems


def _font_supports_hebrew(family: str) -> bool:
    systems = {
        QFontDatabase.writingSystemName(system)
        for system in QFontDatabase.writingSystems(family)
    }
    return "Hebrew" in systems
