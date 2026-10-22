"""P2 交互回归测试：模拟鼠标拖拽与键盘，校验双针表盘的拖拽模式、吸附与联动。

不涉及关机逻辑，可反复运行。

表盘交互（见 docs/03-设计规范.md §5.1.1）：
- 抓分针 → 只改分钟，绕过一圈小时 ±1
- 抓时针 → 只改小时，分钟保持不变
- 点空白 → 快速定位，两根针一起跳

运行：.venv\\Scripts\\python.exe scripts/test_interaction.py
"""

from __future__ import annotations

import os

# 测试/截图脚本一律离屏运行：绝不在用户屏幕上弹出任何窗口
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QGuiApplication, QWheelEvent  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui.clock_dial import ClockDial  # noqa: E402
from ui.time_wheels import TimeWheels  # noqa: E402

PASSED = 0
FAILED = 0

CX, CY = 140, 140


def pt(angle: float, radius: float = 100.0) -> QPoint:
    """表盘上某个角度（0 = 12 点，顺时针）的坐标。"""
    return QPoint(
        int(round(CX + math.sin(math.radians(angle)) * radius)),
        int(round(CY - math.cos(math.radians(angle)) * radius)),
    )


def check(name: str, actual, expected) -> None:
    global PASSED, FAILED
    ok = actual == expected
    if ok:
        PASSED += 1
    else:
        FAILED += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  期望 {expected}，实际 {actual}")


def drag(dial: ClockDial, start: QPoint, end: QPoint) -> None:
    QTest.mousePress(dial, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(dial, end)
    QTest.mouseRelease(dial, Qt.MouseButton.LeftButton, pos=end)


def circle_drag(dial: ClockDial) -> None:
    """从 12 点顺时针绕一圈。"""
    QTest.mousePress(dial, Qt.MouseButton.LeftButton, pos=pt(0))
    for angle in (90, 180, 270, 0):
        QTest.mouseMove(dial, pt(angle))
    QTest.mouseRelease(dial, Qt.MouseButton.LeftButton, pos=pt(0))


def wheel(widget, angle_delta_y: int, x: float = 50.0) -> None:
    """模拟滚轮：angle_delta_y 为负表示向下滚。"""
    pos = QPointF(x, 66)
    event = QWheelEvent(
        pos,
        pos,
        QPoint(0, 0),
        QPoint(0, angle_delta_y),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    widget.wheelEvent(event)


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    dial = ClockDial()
    dial.show()

    print("表盘 · 点空白快速定位：")
    dial.set_time(20, 0, animate=False)
    QTest.mouseClick(dial, Qt.MouseButton.LeftButton, pos=pt(90))  # 3 点位置，两根针都不在那
    check("20:00 点 3 点位置 → 15:00", dial.time(), (15, 0))

    print("表盘 · 拖分针：")
    dial.set_time(20, 0, animate=False)
    drag(dial, pt(0), pt(90))  # 分针 0° → 90° = +15 分钟
    check("分针顺时针 90° → 20:15", dial.time(), (20, 15))

    dial.set_time(20, 0, animate=False)
    circle_drag(dial)
    check("分针绕一圈 → 小时 +1 变 21:00", dial.time(), (21, 0))

    dial.set_time(20, 15, animate=False)
    drag(dial, pt(90), pt(84))  # 分针 90° → 84°，退 1 分钟
    hour, minute = dial.time()
    check("松手后分钟吸附到 5 的整数倍", minute % 5, 0)

    print("表盘 · 拖时针：")
    dial.set_time(20, 30, animate=False)
    drag(dial, pt(255), pt(285))  # 20:30 的时针在 255°，拨到 285°
    check("时针 +1 格 → 21:30", dial.time(), (21, 30))

    dial.set_time(20, 32, animate=False)
    drag(dial, pt(256), pt(286))
    check("拖时针不改动分钟（20:32 → 21:32）", dial.time(), (21, 32))

    print("表盘 · 键盘：")
    dial.set_time(20, 30, animate=False)
    dial.setFocus()
    QTest.keyClick(dial, Qt.Key.Key_Right)
    check("右方向键 +1 小时", dial.time(), (21, 30))
    QTest.keyClick(dial, Qt.Key.Key_Left)
    QTest.keyClick(dial, Qt.Key.Key_Left)
    check("左方向键 -2 小时", dial.time(), (19, 30))
    QTest.keyClick(dial, Qt.Key.Key_Up)
    check("上方向键 +1 分钟", dial.time(), (19, 31))
    QTest.keyClick(dial, Qt.Key.Key_Down)
    QTest.keyClick(dial, Qt.Key.Key_Down)
    check("下方向键 -2 分钟", dial.time(), (19, 29))

    print("表盘 · 跨午夜：")
    dial.set_time(23, 59, animate=False)
    QTest.keyClick(dial, Qt.Key.Key_Up)
    check("23:59 再 +1 分钟回到 00:00", dial.time(), (0, 0))

    # ---- 轮盘 ----
    wheels = TimeWheels()
    wheels.show()

    print("轮盘 · 环绕：")
    wheels.set_time(23, 59)
    wheels._step(0, 1)  # noqa: SLF001
    check("小时 23 +1 回到 0", wheels.time()[0], 0)
    wheels._step(1, 1)  # noqa: SLF001
    check("分钟 59 +1 回到 0", wheels.time()[1], 0)
    wheels._step(1, -1)  # noqa: SLF001
    check("分钟 0 -1 回到 59", wheels.time()[1], 59)

    print("轮盘 · 单列滚动：")
    wheels.set_time(10, 20)
    wheels._step(0, 1)  # noqa: SLF001
    check("动小时时分钟不变", wheels.time(), (11, 20))
    wheels._step(1, 1)  # noqa: SLF001
    check("动分钟时小时不变", wheels.time(), (11, 21))

    print("轮盘 · 拖拽方向：")
    wheels.set_time(10, 0)
    QTest.mousePress(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 40))
    QTest.mouseMove(wheels, QPoint(50, 40 + 44 * 2))
    QTest.mouseRelease(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 128))
    check("向下拖两行 = 小时 +2（选下面更大的数）", wheels.time()[0], 12)

    wheels.set_time(10, 0)
    QTest.mousePress(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 128))
    QTest.mouseMove(wheels, QPoint(50, 128 - 44 * 2))
    QTest.mouseRelease(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 40))
    check("向上拖两行 = 小时 -2", wheels.time()[0], 8)

    print("轮盘 · 滚动动画方向：")
    wheels.set_time(10, 0)
    QTest.mousePress(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 40))
    QTest.mouseMove(wheels, QPoint(50, 84))  # 向下拖一行
    check(
        "向下滑动：内容先下移，新值从下方升起",
        wheels._anims[0].startValue(),  # noqa: SLF001
        44.0,
    )
    QTest.mouseRelease(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 84))

    wheels.set_time(10, 0)
    QTest.mousePress(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 84))
    QTest.mouseMove(wheels, QPoint(50, 40))  # 向上拖一行
    check(
        "向上滑动：内容先上移，新值从上方落下",
        wheels._anims[0].startValue(),  # noqa: SLF001
        -44.0,
    )
    QTest.mouseRelease(wheels, Qt.MouseButton.LeftButton, pos=QPoint(50, 40))

    print("轮盘 · 滚轮方向：")
    wheels.set_time(10, 0)
    wheel(wheels, -120)
    check("滚轮向下 = 小时 +1", wheels.time()[0], 11)
    wheel(wheels, 120)
    check("滚轮向上 = 小时 -1", wheels.time()[0], 10)
    wheels.set_time(10, 0)
    wheel(wheels, -360, x=150)
    check("滚轮连滚 3 格 = 分钟 +3", wheels.time(), (10, 3))

    # ---- 联动 ----
    print("双向联动：")
    dial_events: list[tuple[int, int]] = []
    dial.timeChanged.connect(lambda h, m: dial_events.append((h, m)))
    dial.timeChanged.connect(lambda h, m: wheels.set_time(h, m))
    wheels.timeChanged.connect(lambda h, m: dial.set_time(h, m, animate=False))

    dial.set_time(20, 0, animate=False)
    wheels.set_time(20, 0)
    drag(dial, pt(0), pt(270))  # 分针逆时针 90° → 19:45
    check("拖表盘后轮盘同步", wheels.time(), dial.time())
    check("拖表盘至少广播一次", len(dial_events) > 0, True)

    before = dial.time()
    wheels._step(1, 3)  # noqa: SLF001
    check("滚轮盘后表盘同步", dial.time(), wheels.time())
    check("联动没有形成循环", dial.time() != before, True)

    print(f"\n通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
