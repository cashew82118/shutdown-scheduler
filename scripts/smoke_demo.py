"""P2 截图验证：渲染 demo 窗口的几种状态，便于人工检查视觉与联动。

不涉及关机逻辑。产物：logs/demo_*.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtCore import Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QGuiApplication  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui.clock_demo import ClockDemo  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "logs"

# (文件名, hour, minute)
SCENES = [
    ("demo_1_normal", 20, 30),
    ("demo_2_arc", 15, 45),
    ("demo_3_nextday", 7, 5),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    window = ClockDemo()
    window.setWindowTitle("P2 验证")

    index = 0

    def shot() -> None:
        nonlocal index
        if index >= len(SCENES):
            app.quit()
            return

        name, hour, minute = SCENES[index]
        window._wheels.set_time(hour, minute)  # noqa: SLF001
        window._on_wheels_changed(hour, minute)  # noqa: SLF001
        QTimer.singleShot(450, lambda: capture(name))

    def capture(name: str) -> None:
        nonlocal index
        path = OUT_DIR / f"{name}.png"
        window.grab().save(str(path))
        print(f"SHOT {path.name}")
        index += 1
        QTimer.singleShot(100, shot)

    QTimer.singleShot(500, shot)
    code = app.exec()

    # 校验两根针的角度换算（不依赖鼠标事件）
    dial = window._dial  # noqa: SLF001
    checks = [
        ((3, 0), 90.0, 0.0),
        ((15, 45), 112.5, 270.0),
        ((0, 0), 0.0, 0.0),
        ((23, 59), 359.5, 354.0),
    ]
    print("指针角度:")
    for (hour, minute), expected_h, expected_m in checks:
        dial.set_time(hour, minute, animate=False)
        ah, am = dial._hour_angle(), dial._minute_angle()  # noqa: SLF001
        ok = abs(ah - expected_h) < 0.01 and abs(am - expected_m) < 0.01
        print(f"  {'PASS' if ok else 'FAIL'}  {hour:02d}:{minute:02d} -> 时针 {ah}°, 分针 {am}°")
    return code


if __name__ == "__main__":
    sys.exit(main())
