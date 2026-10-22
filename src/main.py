"""程序入口。

职责：日志初始化、高 DPI 策略、单实例检测、创建 QApplication、显示主窗口。
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

# 允许以 `python src/main.py` 方式直接运行时正确导入 ui / core 包
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.main_window import MainWindow  # noqa: E402

LOGGER = logging.getLogger("app")
SERVER_NAME = "ShutdownScheduler.SingleInstance"


def _base_dir() -> Path:
    """打包后取 exe 所在目录，开发期取项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return SRC_DIR.parent


def _setup_logging() -> None:
    log_dir = _base_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def _install_excepthook() -> None:
    def handle(exc_type, exc_value, exc_tb) -> None:
        LOGGER.exception("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))
        QMessageBox.critical(
            None,
            "定时关机",
            f"程序遇到错误，已记录到日志。\n\n{exc_type.__name__}: {exc_value}",
        )

    sys.excepthook = handle


def _acquire_single_instance() -> QLocalServer | None:
    """已有实例时通知它显示窗口并返回 None；否则返回新建的 server。"""
    probe = QLocalSocket()
    probe.connectToServer(SERVER_NAME)
    if probe.waitForConnected(300):
        probe.write(b"activate")
        probe.flush()
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return None

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        LOGGER.warning("单实例服务启动失败：%s", server.errorString())
        return QLocalServer()  # 不代表已有实例，返回一个未监听的占位
    return server


def _bind_activation(server: QLocalServer, window: MainWindow) -> None:
    def on_new_connection() -> None:
        connection = server.nextPendingConnection()
        if connection is not None:
            connection.disconnectFromServer()
        window.showNormal()
        window.raise_()
        window.activateWindow()

    server.newConnection.connect(on_new_connection)


def main() -> int:
    _setup_logging()
    LOGGER.info("启动，Python %s", sys.version.split()[0])

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ShutdownScheduler")
    app.setApplicationDisplayName("定时关机")
    # 关掉主窗口不等于退出：是否退出由托盘菜单与关窗设置决定
    app.setQuitOnLastWindowClosed(False)

    _install_excepthook()

    if "--selftest" in sys.argv:
        # 打包后用 exe --selftest 验证：不显示窗口、不建托盘，只确认 Qt 与界面能正常构建
        window = MainWindow(enable_tray=False)
        LOGGER.info("自检通过，窗口 %sx%s", window.width(), window.height())
        return 0

    server = _acquire_single_instance()
    if server is None:
        LOGGER.info("已有实例在运行，激活后退出")
        return 0

    window = MainWindow()
    window.show()
    _bind_activation(server, window)
    LOGGER.info("主窗口已显示")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
