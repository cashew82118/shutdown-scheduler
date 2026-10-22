"""主窗口：把表盘、轮盘、预设按钮、设定/取消、状态条串成一个完整软件。

职责边界（见 docs/02-技术方案.md §3）：
- 本文件不直接调用 subprocess / shutdown，命令走 core.shutdown_service，
  动作分发走 core.action_service
- 界面文案一律从 ui.strings 取

v1.1：托盘常驻、关窗询问、设置窗（FR-10 ~ FR-12）；
      动作类型、常驻执行、主题色联动（FR-13 / FR-14）。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import action_service, autostart, shutdown_service
from core.action_service import (
    HIBERNATE,
    LOCK,
    RESTART,
    SHUTDOWN,
)
from core.clock_math import resolve_target, seconds_until
from core.plan_store import Plan, PlanStore
from core.settings import (
    CLOSE_EXIT,
    CLOSE_TRAY,
    Settings,
    SettingsStore,
)
from ui import strings, styles
from ui.clock_dial import ClockDial
from ui.close_choice_dialog import CloseChoiceDialog
from ui.formatting import format_clock, format_remaining, format_when
from ui.icons import GEAR, IconButton
from ui.resources import icon_path
from ui.settings_dialog import SettingsDialog
from ui.time_wheels import TimeWheels
from ui.tray_icon import TrayIcon

LOGGER = logging.getLogger(__name__)
DOT_IDLE = "#C9CED7"
GEAR_SIZE = (30, 26)

ACTION_NAMES: dict[str, str] = {
    SHUTDOWN: strings.ACTION_SHUTDOWN,
    RESTART: strings.ACTION_RESTART,
    LOCK: strings.ACTION_LOCK,
    HIBERNATE: strings.ACTION_HIBERNATE,
}

ACTION_ORDER: tuple[str, ...] = (SHUTDOWN, RESTART, LOCK, HIBERNATE)


def autostart_target() -> str:
    """开机自启要写入的启动命令：打包后是 exe，开发期是 python + 脚本。"""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    script = Path(sys.argv[0]).resolve()
    return f'"{Path(sys.executable).resolve()}" "{script}"'


class MainWindow(QMainWindow):
    def __init__(
        self,
        store: PlanStore | None = None,
        settings_store: SettingsStore | None = None,
        enable_tray: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle(strings.APP_TITLE)
        self.setFixedSize(styles.WINDOW_WIDTH, styles.WINDOW_HEIGHT)

        self._store = store if store is not None else PlanStore()
        self._settings_store = (
            settings_store if settings_store is not None else SettingsStore()
        )
        self._settings: Settings = self._settings_store.load()
        self._plan: Plan | None = self._store.load()

        self._hour, self._minute = self._initial_selection()

        self._build_ui()
        self._wire_signals()
        self._setup_timers()
        self._setup_tray(enable_tray)
        self._apply_theme()

        self._dial.set_time(self._hour, self._minute, animate=False)
        self._wheels.set_time(self._hour, self._minute)
        self._refresh_selection_labels()
        self._refresh_status()

    # -- 初始化 -----------------------------------------------------------

    def _initial_selection(self) -> tuple[int, int]:
        """有计划就显示计划时间，否则默认给一小时后。"""
        if self._plan is not None:
            moment = self._plan.target_datetime
            return moment.hour, moment.minute

        start = datetime.now() + timedelta(hours=1)
        return start.hour, (start.minute // 5) * 5

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("Root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(styles.PADDING_X, 12, styles.PADDING_X, 12)
        outer.setSpacing(0)

        outer.addLayout(self._build_mode_row())
        outer.addSpacing(4)
        outer.addLayout(self._build_clock_row())

        self._dial = ClockDial(root)
        self._wheels = TimeWheels(root)

        outer.addSpacing(6)
        outer.addWidget(self._dial, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(8)
        outer.addWidget(self._wheels, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(12)

        outer.addLayout(self._build_preset_row(root))
        outer.addSpacing(12)

        self._set_btn = self._make_button(
            root, strings.BTN_SET, "Primary", styles.PRIMARY_HEIGHT
        )
        outer.addWidget(self._set_btn)
        outer.addSpacing(8)

        self._cancel_btn = self._make_button(
            root, strings.BTN_CANCEL, "Secondary", styles.SECONDARY_HEIGHT
        )
        outer.addWidget(self._cancel_btn)
        outer.addSpacing(12)

        outer.addWidget(self._build_status_bar(root))

    def _build_mode_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._mode_dot = QLabel(self)
        self._mode_dot.setFixedSize(6, 6)

        self._mode_label = QLabel(self)
        self._mode_label.setObjectName("ModeHint")

        self._gear = IconButton(GEAR, GEAR_SIZE, tooltip=strings.TRAY_SETTINGS, parent=self)
        self._gear.clicked.connect(self._open_settings)

        row.addWidget(self._mode_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._mode_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        row.addWidget(self._gear, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def _build_clock_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._day_label = QLabel(strings.DAY_TODAY)
        self._day_label.setObjectName("Day")

        self._clock_label = QLabel("00:00")
        self._clock_label.setObjectName("Clock")

        row.addStretch(1)
        row.addWidget(self._day_label, 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self._clock_label, 0, Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)
        return row

    def _build_preset_row(self, parent: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        for text, minutes in strings.PRESET_BUTTONS:
            button = self._make_button(parent, text, "Preset", styles.PRESET_HEIGHT)
            button.clicked.connect(
                lambda _checked=False, value=minutes: self._on_preset(value)
            )
            row.addWidget(button)
        return row

    @staticmethod
    def _make_button(parent: QWidget, text: str, style_id: str, height: int) -> QPushButton:
        button = QPushButton(text, parent)
        button.setObjectName(style_id)
        button.setFixedHeight(height)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_status_bar(self, parent: QWidget) -> QFrame:
        bar = QFrame(parent)
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(styles.STATUS_HEIGHT)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        self._status_dot = QLabel(bar)
        self._status_dot.setFixedSize(6, 6)

        self._status_text = QLabel(strings.STATUS_NONE, bar)
        self._status_text.setObjectName("StatusText")

        layout.addWidget(self._status_dot)
        layout.addWidget(self._status_text, 1)
        return bar

    def _wire_signals(self) -> None:
        self._dial.timeChanged.connect(self._on_dial_changed)
        self._wheels.timeChanged.connect(self._on_wheels_changed)
        self._set_btn.clicked.connect(self._on_set)
        self._cancel_btn.clicked.connect(self._on_cancel)

    def _setup_timers(self) -> None:
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)

        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._refresh_status)

        self._resident_timer = QTimer(self)
        self._resident_timer.setSingleShot(True)
        self._resident_timer.timeout.connect(self._on_resident_fire)

    def _setup_tray(self, enabled: bool) -> None:
        self._tray: TrayIcon | None = None
        if not enabled:
            return
        try:
            self._tray = TrayIcon(
                icon_path(),
                on_show=self._restore_from_tray,
                on_settings=self._open_settings,
                on_quit=self._quit_app,
                parent=self,
            )
        except Exception as exc:  # noqa: BLE001 托盘不可用不该让程序起不来
            LOGGER.warning("托盘初始化失败：%s", exc)
            self._tray = None

    # -- 主题与模式（FR-14）-----------------------------------------------

    def _mode_name(self, action: str) -> str:
        return ACTION_NAMES.get(action, action)

    def _apply_theme(self) -> None:
        action = self._settings.action
        accent = styles.theme_accent(action)

        self.setStyleSheet(styles.build_qss(action))
        self._dial.set_accent(accent)
        self._wheels.set_accent(accent)
        self._set_btn.setText(
            strings.BTN_SET_TEMPLATE.format(mode=self._mode_name(action))
        )

        self._mode_dot.setStyleSheet(f"background-color: {accent}; border-radius: 3px;")
        self._mode_label.setText(
            strings.MODE_HINT.format(mode=self._mode_name(action))
        )

        self._refresh_selection_labels()
        self._refresh_tray_tooltip()

    # -- 选时联动 ---------------------------------------------------------

    def _on_dial_changed(self, hour: int, minute: int) -> None:
        self._hour, self._minute = hour, minute
        self._wheels.set_time(hour, minute, animate=True)
        self._refresh_selection_labels()

    def _on_wheels_changed(self, hour: int, minute: int) -> None:
        self._hour, self._minute = hour, minute
        self._dial.set_time(hour, minute, animate=True)
        self._refresh_selection_labels()

    def _refresh_selection_labels(self) -> None:
        now = datetime.now()
        target = resolve_target(now, self._hour, self._minute)

        self._clock_label.setText(format_clock(self._hour, self._minute))
        day_text = strings.DAY_TOMORROW if target.is_next_day else strings.DAY_TODAY
        self._day_label.setText(day_text)
        color = (
            styles.theme_accent(self._settings.action)
            if target.is_next_day
            else styles.TEXT_SUB
        )
        self._day_label.setStyleSheet(
            f"font-family: {styles.FONT_FAMILY}; font-size: 13px; color: {color};"
        )

    # -- 设定（FR-13）-----------------------------------------------------

    def _on_set(self) -> None:
        now = datetime.now()
        target = resolve_target(now, self._hour, self._minute)
        seconds = seconds_until(target.moment, now)
        self._commit_plan(seconds, target.moment, ask_before_replace=True, source="dial")

    def _on_preset(self, minutes: int) -> None:
        now = datetime.now()
        target = now + timedelta(minutes=minutes)
        seconds = int((target - now).total_seconds())

        # 预设按钮是一次性明确动作：直接替换，不额外确认
        self._commit_plan(seconds, target, ask_before_replace=False, source="preset")

    def _commit_plan(
        self, seconds: int, target: datetime, ask_before_replace: bool, source: str
    ) -> None:
        action = self._settings.action
        now = datetime.now()
        when = format_when(target, now)
        replaced = False

        # 1. 本地记录里有计划：按需确认后先取消
        if self._plan is not None:
            if ask_before_replace:
                old_when = format_when(self._plan.target_datetime, now)
                if not self._confirm(
                    strings.DLG_OVERWRITE_TITLE,
                    strings.DLG_OVERWRITE_TEXT.format(when=old_when),
                ):
                    return
            self._cancel_active_plan()
            replaced = True

        # 2. 下发
        outcome = action_service.arm(action, seconds)

        # 3. 系统里还有别人设的关机计划（仅关机/重启会遇到）
        if outcome.code == 1190:
            if not self._confirm(
                strings.DLG_EXTERNAL_TITLE,
                strings.DLG_EXTERNAL_TEXT.format(when=when),
            ):
                return
            shutdown_service.cancel()
            outcome = action_service.arm(action, seconds)
            replaced = True

        if not outcome.ok:
            template = strings.ERR_REPLACED_FAILED if replaced else strings.ERR_SET_FAILED
            self._show_error(template.format(message=outcome.message))
            return

        plan = Plan(
            target_ts=target.timestamp(),
            target_text=target.strftime("%Y-%m-%d %H:%M"),
            created_ts=now.timestamp(),
            seconds=seconds,
            source=source,
            action=action,
        )
        self._store.save(plan)
        self._plan = plan

        if outcome.deferred:
            self._start_resident_timer(seconds)
        else:
            self._resident_timer.stop()

        self._refresh_status()

    # -- 常驻执行 ---------------------------------------------------------

    def _start_resident_timer(self, seconds: int) -> None:
        """到点由本进程执行锁定/休眠。QTimer 毫秒上限约 24.8 天，够用。"""
        self._resident_timer.stop()
        self._resident_timer.start(min(seconds * 1000, 2**31 - 1))
        LOGGER.info("常驻计划已挂载，%s 秒后执行", seconds)

    def _stop_resident_timer(self) -> None:
        self._resident_timer.stop()

    def _on_resident_fire(self) -> None:
        if self._plan is None:
            return
        action = self._plan.action
        ok = action_service.execute_now(action)
        self._clear_local_plan()
        self._refresh_status()
        mode = self._mode_name(action)
        if ok:
            self._show_notice(f"已执行{mode}")
        else:
            self._show_error(f"{mode}执行失败，详见日志")

    # -- 取消 -------------------------------------------------------------

    def _on_cancel(self) -> None:
        if self._plan is None:
            return

        now = datetime.now()
        when = format_when(self._plan.target_datetime, now)
        if not self._confirm(
            strings.DLG_CANCEL_TITLE,
            strings.DLG_CANCEL_TEXT.format(when=when),
        ):
            return

        outcome = action_service.cancel(self._plan.action)
        # 1116 表示系统里本来就没有计划，对用户来说结果一致
        if outcome.ok or outcome.code == 1116:
            self._clear_local_plan()
            self._stop_resident_timer()
            self._refresh_status()
            self._show_notice(strings.MSG_CANCELLED)
        else:
            self._show_error(strings.ERR_CANCEL_FAILED.format(message=outcome.message))

    def _clear_local_plan(self) -> None:
        self._store.clear()
        self._plan = None

    def _cancel_active_plan(self) -> None:
        """内部取消：不弹确认、不打扰状态条，调用方决定后续提示。"""
        if self._plan is None:
            return
        action_service.cancel(self._plan.action)
        self._stop_resident_timer()
        self._clear_local_plan()

    # -- 状态刷新 ---------------------------------------------------------

    def _on_tick(self) -> None:
        if self._plan is None:
            self._tick_timer.stop()
            return
        self._update_countdown()

    def _refresh_status(self) -> None:
        if self._plan is None:
            self._set_dot(DOT_IDLE)
            self._status_text.setStyleSheet("")
            self._status_text.setTextFormat(Qt.TextFormat.PlainText)
            self._status_text.setText(strings.STATUS_NONE)
            self._cancel_btn.setEnabled(False)
            self._tick_timer.stop()
            self._refresh_tray_tooltip()
            return

        self._cancel_btn.setEnabled(True)
        self._update_countdown()
        if not self._tick_timer.isActive():
            self._tick_timer.start()

    def _update_countdown(self) -> None:
        plan = self._plan
        if plan is None:
            return

        now = datetime.now()
        remaining = int((plan.target_datetime - now).total_seconds())
        if remaining <= 0:
            # 目标时刻已过，记录失效
            self._clear_local_plan()
            self._refresh_status()
            return

        when = format_when(plan.target_datetime, now)
        mode = self._mode_name(plan.action)
        suffix = (
            strings.STATUS_RESIDENT_HINT
            if action_service.is_resident(plan.action)
            else ""
        )
        self._set_dot(styles.theme_accent(plan.action))
        self._status_text.setStyleSheet(
            f"font-family: {styles.FONT_FAMILY}; font-size: 12px; color: {styles.TEXT};"
        )
        self._status_text.setTextFormat(Qt.TextFormat.RichText)
        self._status_text.setText(
            strings.STATUS_PLANNED.format(
                when=when,
                mode=mode,
                remaining=f"<b>{format_remaining(remaining)}</b>{suffix}",
            )
        )
        self._refresh_tray_tooltip()

    def _refresh_tray_tooltip(self) -> None:
        if self._tray is None:
            return
        if not self._settings.tray_countdown:
            self._tray.set_tooltip(strings.TRAY_TOOLTIP)
            return
        if self._plan is None:
            self._tray.set_tooltip(strings.STATUS_NONE)
            return

        now = datetime.now()
        remaining = max(int((self._plan.target_datetime - now).total_seconds()), 0)
        self._tray.set_tooltip(
            strings.STATUS_PLANNED.format(
                when=format_when(self._plan.target_datetime, now),
                mode=self._mode_name(self._plan.action),
                remaining=format_remaining(remaining),
            )
        )

    def _show_error(self, message: str) -> None:
        self._cancel_btn.setEnabled(self._plan is not None)
        self._set_dot(styles.DANGER)
        self._status_text.setStyleSheet(
            f"font-family: {styles.FONT_FAMILY}; font-size: 12px; color: {styles.DANGER};"
        )
        self._status_text.setTextFormat(Qt.TextFormat.PlainText)
        self._status_text.setText(message)
        self._error_timer.start(3000)

    def _show_notice(self, message: str) -> None:
        self._set_dot(styles.OK)
        self._status_text.setStyleSheet(
            f"font-family: {styles.FONT_FAMILY}; font-size: 12px; color: {styles.OK};"
        )
        self._status_text.setTextFormat(Qt.TextFormat.PlainText)
        self._status_text.setText(message)
        self._error_timer.start(3000)

    def _set_dot(self, color: str) -> None:
        self._status_dot.setStyleSheet(f"background-color: {color}; border-radius: 3px;")

    # -- 对话框 -----------------------------------------------------------

    def _confirm(
        self,
        title: str,
        text: str,
        confirm_text: str = strings.BTN_CONFIRM,
        dismiss_text: str = strings.BTN_DISMISS,
    ) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Question)

        confirm_button = box.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
        dismiss_button = box.addButton(dismiss_text, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(dismiss_button)  # 默认焦点在「再想想」
        box.exec()
        return box.clickedButton() is confirm_button

    # -- 设置与主题切换 ----------------------------------------------------

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if not dialog.exec():
            return

        new_settings = dialog.result()

        # 切换动作类型会作废当前计划（FR-13）
        if new_settings.action != self._settings.action and self._plan is not None:
            now = datetime.now()
            if not self._confirm(
                strings.DLG_SWITCH_ACTION_TITLE,
                strings.DLG_SWITCH_ACTION_TEXT.format(
                    when=format_when(self._plan.target_datetime, now),
                    mode=self._mode_name(self._plan.action),
                ),
            ):
                return
            self._cancel_active_plan()

        self._apply_settings(new_settings)

    def _apply_settings(self, settings: Settings) -> None:
        old = self._settings
        self._settings = settings
        try:
            self._settings_store.save(settings)
        except OSError as exc:
            self._show_error(strings.ERR_SETTINGS_SAVE_FAILED.format(message=exc))
            return

        if settings.autostart != old.autostart:
            if settings.autostart:
                autostart.enable(autostart_target())
            else:
                autostart.disable()

        if settings.action != old.action:
            self._apply_theme()

        self._show_notice(strings.MSG_SETTINGS_SAVED)
        self._refresh_tray_tooltip()

    # -- 托盘与退出 --------------------------------------------------------

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _maybe_warn_resident(self) -> bool:
        """计划依赖常驻时，退出前强警告（FR-13）。返回 True 表示允许退出。"""
        if self._plan is None or not action_service.is_resident(self._plan.action):
            return True
        mode = self._mode_name(self._plan.action)
        return self._confirm(
            strings.WARN_RESIDENT_TITLE,
            strings.WARN_RESIDENT_TEXT.format(mode=mode),
        )

    def _quit_app(self) -> None:
        if self._maybe_warn_resident():
            QApplication.instance().quit()

    def _hide_to_tray(self) -> None:
        self.hide()

    def closeEvent(self, event) -> None:
        action = self._settings.close_action

        if action == CLOSE_EXIT:
            if self._maybe_warn_resident():
                QApplication.instance().quit()
                event.accept()
            else:
                event.ignore()
            return

        if action == CLOSE_TRAY:
            self._hide_to_tray()
            event.ignore()
            return

        # 每次询问
        dialog = CloseChoiceDialog(self, theme_action=self._settings.action)
        dialog.exec()
        choice, remember = dialog.result()

        if remember:
            self._apply_settings(
                Settings(
                    autostart=self._settings.autostart,
                    tray_countdown=self._settings.tray_countdown,
                    close_action=CLOSE_TRAY if choice == "tray" else CLOSE_EXIT,
                    action=self._settings.action,
                )
            )

        if choice == "exit":
            if self._maybe_warn_resident():
                QApplication.instance().quit()
                event.accept()
            else:
                event.ignore()
        else:
            self._hide_to_tray()
            event.ignore()

    def changeEvent(self, event) -> None:
        # 最小化也进托盘，和「关闭窗口」的托盘行为保持一致
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self._hide_to_tray()
            event.ignore()
            return
        super().changeEvent(event)
