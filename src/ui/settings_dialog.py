"""设置对话框。

三个设置项：开机自启、托盘显示剩余时间、关窗行为。
控件用自绘的 ToggleSwitch / SegmentedControl，不用 QCheckBox / QRadioButton。
返回修改后的 Settings；点取消则不改动原设置。

对应需求 FR-10 / FR-11 / FR-12。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.action_service import ACTIONS
from core.settings import (
    CLOSE_ACTIONS,
    CLOSE_ASK,
    CLOSE_EXIT,
    CLOSE_TRAY,
    Settings,
)
from ui import strings, styles
from ui.controls import SegmentedControl, ToggleSwitch  # noqa: F401 (controls re-imported)
from ui.controls import SegmentedControl, ToggleSwitch

ACTION_LABELS: dict[str, str] = {
    CLOSE_ASK: strings.SETTINGS_CLOSE_ASK,
    CLOSE_TRAY: strings.SETTINGS_CLOSE_TRAY,
    CLOSE_EXIT: strings.SETTINGS_CLOSE_EXIT,
}


class _SettingRow(QWidget):
    """一行设置：左边标题+说明，右边控件。"""

    def __init__(self, title: str, hint: str, control: QWidget, parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        text = QVBoxLayout()
        text.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("SettingLabel")
        text.addWidget(title_label)

        hint_label = QLabel(hint)
        hint_label.setObjectName("SettingHint")
        text.addWidget(hint_label)

        row.addLayout(text, 1)
        row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Root")
        self.setStyleSheet(styles.build_qss(settings.action))
        self.setWindowTitle(strings.SETTINGS_TITLE)
        self.setFixedSize(400, 400)

        accent = styles.theme_accent(settings.action)

        self._autostart_toggle = ToggleSwitch(
            settings.autostart, on_color=accent
        )
        self._tray_toggle = ToggleSwitch(
            settings.tray_countdown, on_color=accent
        )

        actions = list(CLOSE_ACTIONS)
        self._close_segment = SegmentedControl(
            [ACTION_LABELS[a] for a in actions],
            current=actions.index(settings.close_action),
        )

        self._action_names = {
            "shutdown": strings.ACTION_SHUTDOWN,
            "restart": strings.ACTION_RESTART,
            "lock": strings.ACTION_LOCK,
            "hibernate": strings.ACTION_HIBERNATE,
        }
        action_order = list(ACTIONS)
        self._action_segment = SegmentedControl(
            [self._action_names[a] for a in action_order],
            current=action_order.index(settings.action),
        )
        self._action_segment.selection_changed.connect(
            lambda _i: self._refresh_theme()
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(0)

        layout.addWidget(
            _SettingRow(
                strings.SETTINGS_AUTOSTART,
                strings.SETTINGS_AUTOSTART_HINT,
                self._autostart_toggle,
            )
        )
        layout.addSpacing(16)

        layout.addWidget(
            _SettingRow(
                strings.SETTINGS_TRAY_COUNTDOWN,
                strings.SETTINGS_TRAY_COUNTDOWN_HINT,
                self._tray_toggle,
            )
        )
        layout.addSpacing(16)

        close_title = QLabel(strings.SETTINGS_CLOSE_ACTION)
        close_title.setObjectName("SettingLabel")
        layout.addWidget(close_title)
        layout.addSpacing(8)
        layout.addWidget(self._close_segment, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(16)

        action_title = QLabel(strings.SETTINGS_ACTION)
        action_title.setObjectName("SettingLabel")
        layout.addWidget(action_title)
        layout.addSpacing(8)
        layout.addWidget(self._action_segment, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(1)
        layout.addLayout(self._build_buttons())

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        cancel = QPushButton(strings.SETTINGS_CANCEL)
        cancel.setObjectName("Secondary")
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)

        save = QPushButton(strings.SETTINGS_SAVE)
        save.setObjectName("Primary")
        save.setFixedHeight(38)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)

        row.addWidget(cancel, 1)
        row.addWidget(save, 1)
        return row

    def _refresh_theme(self) -> None:
        """动作类型切换时，设置窗自己的主题色立即跟着变。"""
        action = self._current_action()
        accent = styles.theme_accent(action)
        self.setStyleSheet(styles.build_qss(action))
        self._autostart_toggle.set_on_color(accent)
        self._tray_toggle.set_on_color(accent)

    def _current_action(self) -> str:
        return list(ACTIONS)[self._action_segment.current]

    def result(self) -> Settings:
        actions = list(CLOSE_ACTIONS)
        close_action = actions[self._close_segment.current]
        return Settings(
            autostart=self._autostart_toggle.checked,
            tray_countdown=self._tray_toggle.checked,
            close_action=close_action,
            action=self._current_action(),
        )
