from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_TERMINAL_THEME = "Hacker Neon"

# Third-party palette credits and license texts: THIRD_PARTY_NOTICES.md.
TERMINAL_THEMES: dict[str, dict[str, str]] = {
    "Hacker Neon": {
        "foreground": "#d7fff1",
        "background": "#05090b",
        "cursor": "#28f0a4",
        "selection": "#123c4a",
    },
    "PuTTY Classic": {
        "foreground": "#ffffff",
        "background": "#000000",
        "cursor": "#00ff00",
        "selection": "#0060a8",
    },
    "PowerShell": {
        "foreground": "#f2f2f2",
        "background": "#012456",
        "cursor": "#ffffff",
        "selection": "#2a6fbd",
    },
    "Solarized Dark": {
        "foreground": "#839496",
        "background": "#002b36",
        "cursor": "#93a1a1",
        "selection": "#073642",
    },
    "Dracula": {
        "foreground": "#f8f8f2",
        "background": "#282a36",
        "cursor": "#50fa7b",
        "selection": "#44475a",
    },
    "Nord": {
        "foreground": "#d8dee9",
        "background": "#2e3440",
        "cursor": "#88c0d0",
        "selection": "#434c5e",
    },
    "Gruvbox Dark": {
        "foreground": "#ebdbb2",
        "background": "#282828",
        "cursor": "#fabd2f",
        "selection": "#504945",
    },
}


class TerminalSettings(BaseModel):
    theme_name: str = DEFAULT_TERMINAL_THEME
    font_family: str = "Cascadia Mono"
    font_size: int = Field(default=14, ge=8, le=48)
    foreground: str = "#d7fff1"
    background: str = "#05090b"
    cursor: str = "#28f0a4"
    selection: str = "#123c4a"
    scrollback_lines: int = Field(default=5000, ge=200, le=200000)
    columns: int = Field(default=100, ge=20, le=400)
    rows: int = Field(default=30, ge=5, le=120)
    parser_backend: str = Field(default="pyte", pattern="^(simple|pyte)$")


class AppSettings(BaseModel):
    terminal: TerminalSettings = Field(default_factory=TerminalSettings)
    confirm_unknown_hosts: bool = True
    start_with_hebrew_proof: bool = False
