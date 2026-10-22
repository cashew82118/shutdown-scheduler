"""托盘图标。

职责：常驻托盘、双击恢复主窗口、右键菜单（显示窗口 / 设置 / 退出）、
tooltip 显示状态。图标本身不绘制，交给 resources.icon_path()。

对应需求 FR-10 / FR-12。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from ui import strings

LOGGER = logging.getLogger(__name__)


class TrayIcon:
    def __init__(
        self,
        icon_path: Path,
        on_show,
        on_settings,
        on_quit,
        parent=None,
        visible: bool = True,
    ) -> None:
        self._tray = QSystemTrayIcon(parent)
        self._tray.setIcon(QIcon(str(icon_path)))
        self._tray.setToolTip(strings.TRAY_TOOLTIP)
        self._tray.activated.connect(self._on_activated)
        if visible:
            self._tray.show()

        self._on_show = on_show
        self._on_settings = on_settings
        self._on_quit = on_quit

        menu = QMenu(parent)
        self._show_action = QAction(strings.TRAY_SHOW, menu)
        self._show_action.triggered.connect(self._handle_show)
        self._settings_action = QAction(strings.TRAY_SETTINGS, menu)
        self._settings_action.triggered.connect(self._handle_settings)
        self._quit_action = QAction(strings.TRAY_QUIT, menu)
        self._quit_action.triggered.connect(self._handle_quit)

        menu.addAction(self._show_action)
        menu.addAction(self._settings_action)
        menu.addSeparator()
        menu.addAction(self._quit_action)
        self._tray.setContextMenu(menu)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            LOGGER.warning("系统托盘不可用，托盘图标不会显示")

    # -- 对外接口 ---------------------------------------------------------

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def set_tooltip(self, text: str) -> None:
        self._tray.setToolTip(text)

    def show_message(self, title: str, body: str, msecs: int = 3000) -> None:
        """托盘气泡。仅用于极少数提示，不做关机前提醒。"""
        self._tray.showMessage(title, body, msecs=msecs)

    def hide(self) -> None:
        self._tray.hide()

    # -- 内部 -------------------------------------------------------------

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._handle_show()

    def _handle_show(self) -> None:
        if callable(self._on_show):
            self._on_show()

    def _handle_settings(self) -> None:
        if callable(self._on_settings):
            self._on_settings()

    def _handle_quit(self) -> None:
        if callable(self._on_quit):
            self._on_quit()
