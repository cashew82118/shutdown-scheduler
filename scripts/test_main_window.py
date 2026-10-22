"""P3 功能回归：预设设定、状态恢复、取消、覆盖、倒计时格式。

会真实下发关机计划，因此：
- 时间一律 30 分钟以上（远大于 600 秒的铁律）
- `finally` 兜底取消，并验证系统最终返回 1116
- 只使用临时记录文件，不污染 %LOCALAPPDATA% 里的真实记录

运行：.venv\\Scripts\\python.exe scripts\\test_main_window.py
"""

from __future__ import annotations

import os

# 测试/截图脚本一律离屏运行：绝不在用户屏幕上弹出任何窗口
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from core import shutdown_service  # noqa: E402
from core.plan_store import PlanStore  # noqa: E402
from ui import strings  # noqa: E402
from ui.formatting import format_remaining  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

PASSED = 0
FAILED = 0


def check(name: str, actual, expected) -> None:
    global PASSED, FAILED
    ok = actual == expected
    if ok:
        PASSED += 1
    else:
        FAILED += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  期望 {expected}，实际 {actual}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tmp_path = Path(tempfile.gettempdir()) / "ss_test_main_window.json"
    tmp_path.unlink(missing_ok=True)

    # 开跑前确保系统里没有遗留计划
    shutdown_service.cancel()

    try:
        print("初始状态：")
        window = MainWindow(store=PlanStore(tmp_path), enable_tray=False)
        window.show()
        check("无计划", window._plan, None)  # noqa: SLF001
        check("状态条文案", window._status_text.text(), strings.STATUS_NONE)  # noqa: SLF001
        check("取消按钮禁用", window._cancel_btn.isEnabled(), False)  # noqa: SLF001

        print("预设按钮（30 分钟）：")
        window._on_preset(30)  # noqa: SLF001
        check("计划已建立", window._plan is not None, True)  # noqa: SLF001
        check("本软件记录已落盘", tmp_path.exists(), True)
        check("取消按钮启用", window._cancel_btn.isEnabled(), True)  # noqa: SLF001
        check("秒数正确", window._plan.seconds, 1800)  # noqa: SLF001
        text = window._status_text.text()  # noqa: SLF001
        check("状态条显示剩余时间", "剩余" in text, True)
        print(f"       状态条：{text}")

        print("重启恢复：")
        restored = MainWindow(store=PlanStore(tmp_path), enable_tray=False)
        restored.show()
        check("恢复出计划", restored._plan is not None, True)  # noqa: SLF001
        check("恢复后状态条含剩余", "剩余" in restored._status_text.text(), True)  # noqa: SLF001
        check(
            "选中时间等于计划时间",
            (restored._hour, restored._minute),  # noqa: SLF001
            (restored._plan.target_datetime.hour, restored._plan.target_datetime.minute),  # noqa: SLF001
        )

        print("覆盖（本地已有计划时静默替换）：")
        restored._on_preset(45)  # noqa: SLF001
        check("覆盖后秒数", restored._plan.seconds, 2700)  # noqa: SLF001
        check("记录仍然只有一条", tmp_path.exists(), True)

        print("取消计划：")
        restored._confirm = lambda *a, **k: True  # noqa: SLF001
        restored._on_cancel()  # noqa: SLF001
        check("取消后无计划", restored._plan, None)  # noqa: SLF001
        check("记录已清除", tmp_path.exists(), False)
        check("取消按钮回到禁用", restored._cancel_btn.isEnabled(), False)  # noqa: SLF001
        check("状态条回到无计划", restored._status_text.text(), strings.MSG_CANCELLED)  # noqa: SLF001

        print("格式化：")
        check("3600 秒", format_remaining(3600), "1 小时")
        check("3725 秒", format_remaining(3725), "1 小时 2 分 5 秒")
        check("45 秒", format_remaining(45), "45 秒")
        check("0 秒", format_remaining(0), "0 秒")

    finally:
        result = shutdown_service.cancel()
        print(f"\n[清理] 取消计划 -> {result.code} {result.message}")
        tmp_path.unlink(missing_ok=True)

    final = shutdown_service.cancel()
    check("系统当前无待定关机（返回码 1116）", final.code, 1116)

    print(f"\n通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
