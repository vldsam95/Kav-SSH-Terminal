from __future__ import annotations

from dataclasses import dataclass


# Some ANSI colors overlap the Snazzy/older Dracula palettes.
# See THIRD_PARTY_NOTICES.md for conservative palette attribution.
ANSI_NAMED_COLORS: dict[str, str] = {
    "black": "#0c0c0c",
    "red": "#ff5c57",
    "green": "#5af78e",
    "yellow": "#f3f99d",
    "blue": "#57c7ff",
    "magenta": "#ff6ac1",
    "cyan": "#9aedfe",
    "white": "#f1f1f0",
    "brightblack": "#686868",
    "brightred": "#ff6e67",
    "brightgreen": "#5af78e",
    "brightyellow": "#f4f99d",
    "brightblue": "#57c7ff",
    "brightmagenta": "#ff92d0",
    "brightcyan": "#9aedfe",
    "brightwhite": "#ffffff",
}

ANSI_16_COLORS = [
    ANSI_NAMED_COLORS["black"],
    ANSI_NAMED_COLORS["red"],
    ANSI_NAMED_COLORS["green"],
    ANSI_NAMED_COLORS["yellow"],
    ANSI_NAMED_COLORS["blue"],
    ANSI_NAMED_COLORS["magenta"],
    ANSI_NAMED_COLORS["cyan"],
    ANSI_NAMED_COLORS["white"],
    ANSI_NAMED_COLORS["brightblack"],
    ANSI_NAMED_COLORS["brightred"],
    ANSI_NAMED_COLORS["brightgreen"],
    ANSI_NAMED_COLORS["brightyellow"],
    ANSI_NAMED_COLORS["brightblue"],
    ANSI_NAMED_COLORS["brightmagenta"],
    ANSI_NAMED_COLORS["brightcyan"],
    ANSI_NAMED_COLORS["brightwhite"],
]


@dataclass(frozen=True)
class CellStyle:
    foreground: str | None = None
    background: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    reverse: bool = False


@dataclass(frozen=True)
class StyledSpan:
    start: int
    end: int
    text: str
    style: CellStyle


@dataclass(frozen=True)
class StyledLine:
    text: str
    spans: tuple[StyledSpan, ...]


def ansi_256_color(index: int) -> str | None:
    if index < 0 or index > 255:
        return None
    if index < 16:
        return ANSI_16_COLORS[index]
    if index < 232:
        value = index - 16
        red = value // 36
        green = (value % 36) // 6
        blue = value % 6
        levels = [0, 95, 135, 175, 215, 255]
        return "#{:02x}{:02x}{:02x}".format(levels[red], levels[green], levels[blue])
    shade = 8 + (index - 232) * 10
    return "#{:02x}{:02x}{:02x}".format(shade, shade, shade)


def rgb_color(red: int, green: int, blue: int) -> str | None:
    if any(value < 0 or value > 255 for value in (red, green, blue)):
        return None
    return "#{:02x}{:02x}{:02x}".format(red, green, blue)


def normalize_color(value: str | None) -> str | None:
    if not value or value == "default":
        return None
    if value.startswith("#"):
        return value
    if len(value) == 6 and all(char in "0123456789abcdefABCDEF" for char in value):
        return f"#{value}"
    return ANSI_NAMED_COLORS.get(value.lower(), value)


def styled_line_from_cells(chars: list[str], styles: list[CellStyle]) -> StyledLine:
    text = "".join(chars).rstrip()
    visible_length = len(text)
    if visible_length == 0:
        return StyledLine(text="", spans=())

    spans: list[StyledSpan] = []
    span_start = 0
    current_style = styles[0] if styles else CellStyle()
    for index in range(1, visible_length):
        style = styles[index] if index < len(styles) else CellStyle()
        if style != current_style:
            spans.append(
                StyledSpan(
                    start=span_start,
                    end=index,
                    text=text[span_start:index],
                    style=current_style,
                )
            )
            span_start = index
            current_style = style
    spans.append(
        StyledSpan(
            start=span_start,
            end=visible_length,
            text=text[span_start:visible_length],
            style=current_style,
        )
    )
    return StyledLine(text=text, spans=tuple(spans))
