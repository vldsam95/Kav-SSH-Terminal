from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # pragma: no cover - exercised only without GUI deps.
        raise SystemExit(
            "PySide6 is not installed. Run: python -m pip install -e \".[dev]\""
        ) from exc

    from app.main_window import MainWindow
    from app.theme import apply_hacker_theme

    app = QApplication(sys.argv)
    app.setApplicationName("Kav SSH Terminal")
    app.setOrganizationName("KavSSH")
    app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    apply_hacker_theme(app)

    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
