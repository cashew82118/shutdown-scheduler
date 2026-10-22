"""冒烟测试：渲染主窗口的两种状态并截图后自动退出。

不调用任何 shutdown 命令：「已计划」状态是通过伪造临时记录造出来的，
不会真的在你的系统里挂一个关机计划。

产物：logs/smoke_idle.png（无计划）、logs/smoke_planned.png（已计划）
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.plan_store import Plan, PlanStore  # noqa: E402
from core.settings import Settings  # noqa: E402
from ui.close_choice_dialog import CloseChoiceDialog  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.settings_dialog import SettingsDialog  # noqa: E402
from ui.resources import icon_path  # noqa: E402
from ui.tray_icon import TrayIcon  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "logs"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(tempfile.gettempdir()) / "ss_smoke_planned.json"
    tmp_path.unlink(missing_ok=True)

    app = QApplication(sys.argv)

    # 托盘构造验证：visible=False，绝不在用户托盘里冒出来
    # 注意：必须在 QApplication 之后创建，否则 Qt 直接段错误
    tray = TrayIcon(
        icon_path(),
        on_show=None,
        on_settings=None,
        on_quit=None,
        visible=False,
    )
    tray.set_tooltip("冒烟测试")
    print(f"TRAY OK  系统托盘可用={tray.available} 图标={icon_path().name}")

    idle = MainWindow(store=PlanStore(tmp_path), enable_tray=False)
    idle.grab().save(str(OUT_DIR / "smoke_idle.png"))
    print("SHOT smoke_idle.png")

    # 伪造一条 1 小时 20 分后的计划，仅用于截图
    now = datetime.now()
    target = now + timedelta(minutes=80)
    store = PlanStore(tmp_path)
    store.save(
        Plan(
            target_ts=target.timestamp(),
            target_text=target.strftime("%Y-%m-%d %H:%M"),
            created_ts=now.timestamp(),
            seconds=80 * 60,
            source="preset",
        )
    )

    planned = MainWindow(store=store, enable_tray=False)
    planned.grab().save(str(OUT_DIR / "smoke_planned.png"))
    print("SHOT smoke_planned.png")
    print("状态条:", planned._status_text.text())  # noqa: SLF001

    settings_dlg = SettingsDialog(Settings())
    settings_dlg.grab().save(str(OUT_DIR / "smoke_settings.png"))
    print("SHOT smoke_settings.png")

    close_dlg = CloseChoiceDialog()
    close_dlg.grab().save(str(OUT_DIR / "smoke_close.png"))
    print("SHOT smoke_close.png")

    tmp_path.unlink(missing_ok=True)

    QTimer.singleShot(0, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
