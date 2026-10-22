"""关窗询问对话框。

返回 (choice, remember)：
- choice: "tray" | "exit"
- remember: 是否勾选「不再显示」

对应需求 FR-10。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui import strings, styles
from ui.controls import CheckBox


class CloseChoiceDialog(QDialog):
    def __init__(self, parent=None, theme_action: str = "shutdown") -> None:
        super().__init__(parent)
        self.setObjectName("Root")
        self.setStyleSheet(styles.build_qss(theme_action))
        self.setWindowTitle(strings.DLG_CLOSE_TITLE)
        self.setFixedSize(370, 190)

        self._choice = "exit"
        self._remember = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        text = QLabel(strings.DLG_CLOSE_TEXT)
        text.setObjectName("SettingHint")
        text.setWordWrap(True)
        layout.addWidget(text)

        layout.addStretch(1)

        checkbox = CheckBox(
            strings.DLG_CLOSE_REMEMBER, on_color=styles.theme_accent(theme_action)
        )
        layout.addWidget(checkbox)

        row = QHBoxLayout()
        row.setSpacing(10)

        tray_button = QPushButton(strings.DLG_CLOSE_BTN_TRAY)
        tray_button.setObjectName("Primary")
        tray_button.setFixedHeight(38)
        tray_button.setCursor(Qt.CursorShape.PointingHandCursor)
        tray_button.clicked.connect(lambda: self._finish("tray", checkbox.checked))

        exit_button = QPushButton(strings.DLG_CLOSE_BTN_EXIT)
        exit_button.setObjectName("Secondary")
        exit_button.setFixedHeight(38)
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(lambda: self._finish("exit", checkbox.checked))

        row.addWidget(tray_button, 1)
        row.addWidget(exit_button, 1)
        layout.addLayout(row)

    def _finish(self, choice: str, remember: bool) -> None:
        self._choice = choice
        self._remember = remember
        self.accept()

    def result(self) -> tuple[str, bool]:
        return self._choice, self._remember
