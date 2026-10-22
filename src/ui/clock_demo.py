"""P2 验证用 demo：表盘 + 轮盘双向联动。

不涉及任何关机逻辑，可安全反复运行。
运行：.venv\\Scripts\\python.exe src\\ui\\clock_demo.py 或双击 scripts\\run_clock_demo.bat
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QGuiApplication  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.clock_math import resolve_target  # noqa: E402
from ui import strings, styles  # noqa: E402
from ui.clock_dial import ClockDial  # noqa: E402
from ui.time_wheels import TimeWheels  # noqa: E402


class ClockDemo(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Root")
        self.setStyleSheet(styles.APP_QSS)
        self.setFixedSize(460, 540)

        # 默认给一个未来的时刻，避免一打开就显示「明天」
        start = datetime.now() + timedelta(hours=1)
        self._hour = start.hour
        self._minute = 30 if start.minute < 30 else 0

        self._dial = ClockDial(self)
        self._wheels = TimeWheels(self)
        self._preview = QLabel(self)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            f'font-family: {styles.FONT_FAMILY}; font-size: 34px;'
            f" font-weight: 600; color: {styles.TEXT};"
        )

        hint = QLabel(strings.DIAL_HINT_DRAG, self)
        hint.setObjectName("Detail")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)
        layout.addWidget(self._preview)
        layout.addWidget(self._dial, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._wheels, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(hint)

        self._dial.timeChanged.connect(self._on_dial_changed)
        self._wheels.timeChanged.connect(self._on_wheels_changed)

        self._dial.set_time(self._hour, self._minute, animate=False)
        self._wheels.set_time(self._hour, self._minute)
        self._refresh_preview()

    # -- 联动 -------------------------------------------------------------

    def _on_dial_changed(self, hour: int, minute: int) -> None:
        self._hour, self._minute = hour, minute
        self._wheels.set_time(hour, minute, animate=True)
        self._refresh_preview()

    def _on_wheels_changed(self, hour: int, minute: int) -> None:
        self._hour, self._minute = hour, minute
        self._dial.set_time(hour, minute, animate=True)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        target = resolve_target(datetime.now(), self._hour, self._minute)
        day = strings.DAY_TOMORROW if target.is_next_day else strings.DAY_TODAY
        self._preview.setText(f"{day} {self._hour:02d}:{self._minute:02d}")
        self._preview.setStyleSheet(
            f"font-family: {styles.FONT_FAMILY}; font-size: 34px; font-weight: 600;"
            f" color: {styles.ACCENT if target.is_next_day else styles.TEXT};"
        )


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    window = ClockDemo()
    window.setWindowTitle("P2 验证 · 表盘与轮盘")
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
