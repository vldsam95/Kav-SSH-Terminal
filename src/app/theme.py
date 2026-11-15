from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory


def apply_hacker_theme(app: QApplication) -> None:
    app.setStyle(QStyleFactory.create("Fusion"))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#061014"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#d7f8ef"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#071116"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0d1b21"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#10242b"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#d7f8ef"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#d7f8ef"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#0b1a20"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#d7f8ef"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff6b7a"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#28f0a4"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#03100d"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#5f7f7b"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            background: #061014;
            color: #d7f8ef;
            selection-background-color: #1f6f74;
            selection-color: #f2fffb;
            font-size: 10pt;
        }

        QMainWindow,
        QDialog,
        QMessageBox {
            background: #061014;
        }

        QToolBar {
            background: #071116;
            border: 0;
            border-bottom: 1px solid #16333b;
            spacing: 6px;
            padding: 8px;
        }

        QToolBar::separator {
            background: #16333b;
            width: 1px;
            margin: 5px 8px;
        }

        QToolButton,
        QPushButton {
            background: #0c1d23;
            border: 1px solid #1d4850;
            border-radius: 6px;
            color: #d7f8ef;
            min-height: 26px;
            padding: 6px 12px;
        }

        QToolButton:hover,
        QPushButton:hover {
            background: #102a31;
            border-color: #28f0a4;
            color: #ffffff;
        }

        QToolButton:pressed,
        QPushButton:pressed {
            background: #12363d;
            border-color: #35c8ff;
        }

        QPushButton:default {
            background: #12342f;
            border-color: #28f0a4;
            color: #eafff8;
        }

        QPushButton:disabled,
        QToolButton:disabled {
            background: #0a1519;
            border-color: #14282f;
            color: #5f7f7b;
        }

        QDockWidget {
            titlebar-close-icon: none;
            titlebar-normal-icon: none;
        }

        QDockWidget::title {
            background: #071116;
            border: 1px solid #16333b;
            border-left: 0;
            border-right: 0;
            color: #35c8ff;
            padding: 7px 10px;
            text-align: left;
        }

        QTabWidget::pane {
            background: #05090b;
            border: 1px solid #143039;
            top: -1px;
        }

        QTabBar::tab {
            background: #08151a;
            border: 1px solid #143039;
            border-bottom: 0;
            color: #7ea5a0;
            margin-right: 2px;
            min-width: 118px;
            padding: 8px 12px;
        }

        QTabBar::tab:selected {
            background: #0d2027;
            border-top: 2px solid #28f0a4;
            color: #f2fffb;
        }

        QTabBar::tab:hover:!selected {
            background: #10242b;
            color: #d7f8ef;
        }

        QLineEdit,
        QSpinBox,
        QComboBox,
        QFontComboBox,
        QAbstractSpinBox {
            background: #071116;
            border: 1px solid #1a3b44;
            border-radius: 5px;
            color: #e6fff8;
            min-height: 26px;
            padding: 5px 8px;
        }

        QLineEdit:focus,
        QSpinBox:focus,
        QComboBox:focus,
        QFontComboBox:focus,
        QAbstractSpinBox:focus {
            border-color: #28f0a4;
        }

        QLineEdit:disabled,
        QSpinBox:disabled,
        QComboBox:disabled {
            background: #071014;
            border-color: #14282f;
            color: #597673;
        }

        QComboBox::drop-down,
        QSpinBox::up-button,
        QSpinBox::down-button {
            background: #0e242b;
            border: 0;
            width: 22px;
        }

        QComboBox QAbstractItemView {
            background: #071116;
            border: 1px solid #28f0a4;
            outline: 0;
            selection-background-color: #123c4a;
        }

        QCheckBox {
            spacing: 8px;
        }

        QCheckBox::indicator {
            background: #071116;
            border: 1px solid #1a3b44;
            border-radius: 3px;
            height: 14px;
            width: 14px;
        }

        QCheckBox::indicator:checked {
            background: #28f0a4;
            border-color: #28f0a4;
        }

        QListWidget,
        QTableWidget,
        QTreeView,
        QTableView {
            background: #050b0d;
            alternate-background-color: #0a1519;
            border: 1px solid #143039;
            border-radius: 6px;
            gridline-color: #123039;
            outline: 0;
        }

        QListWidget::item,
        QTableWidget::item {
            border-bottom: 1px solid #0d2027;
            padding: 7px;
        }

        QListWidget::item:selected,
        QTableWidget::item:selected {
            background: #123c4a;
            color: #f2fffb;
        }

        QListWidget::item:hover,
        QTableWidget::item:hover {
            background: #0f252b;
        }

        QHeaderView::section {
            background: #0b1a20;
            border: 0;
            border-bottom: 1px solid #1d4850;
            color: #35c8ff;
            font-weight: 600;
            padding: 7px 9px;
        }

        QMenu {
            background: #071116;
            border: 1px solid #1d4850;
            padding: 5px;
        }

        QMenu::item {
            border-radius: 4px;
            padding: 6px 22px;
        }

        QMenu::item:selected {
            background: #123c4a;
            color: #f2fffb;
        }

        QDialogButtonBox {
            button-layout: 0;
        }

        QScrollBar:vertical,
        QScrollBar:horizontal {
            background: #050b0d;
            border: 0;
            margin: 0;
        }

        QScrollBar:vertical {
            width: 12px;
        }

        QScrollBar:horizontal {
            height: 12px;
        }

        QScrollBar::handle {
            background: #1d4850;
            border-radius: 5px;
            min-height: 28px;
            min-width: 28px;
        }

        QScrollBar::handle:hover {
            background: #28f0a4;
        }

        QScrollBar::add-line,
        QScrollBar::sub-line,
        QScrollBar::add-page,
        QScrollBar::sub-page {
            background: transparent;
            border: 0;
        }

        QStatusBar {
            background: #071116;
            border-top: 1px solid #16333b;
            color: #7ea5a0;
        }

        QSplitter::handle {
            background: #143039;
        }
        """
    )
