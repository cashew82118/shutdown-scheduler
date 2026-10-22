"""V1.1 阶段 2 回归：动作分发、主题色、计划与设置的动作字段。

安全说明：
- 不测试 execute_now 的真实执行（会真的锁屏/休眠）
- 不真实下发重启计划（重启计划忘取消会导致电脑重启），只测参数校验分支
- 关机的真实下发→取消链路已由 test_main_window.py 覆盖

运行：.venv\\Scripts\\python.exe scripts\\test_actions.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from core import action_service, shutdown_service  # noqa: E402
from core.action_service import HIBERNATE, LOCK, RESTART, SHUTDOWN  # noqa: E402
from core.plan_store import PlanStore  # noqa: E402
from core.settings import Settings, SettingsStore  # noqa: E402
from ui import styles  # noqa: E402
from ui.clock_dial import ClockDial  # noqa: E402
from ui.controls import ToggleSwitch  # noqa: E402

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

    print("动作分发：")
    check("锁定是常驻动作", action_service.is_resident(LOCK), True)
    check("休眠是常驻动作", action_service.is_resident(HIBERNATE), True)
    check("关机是系统级", action_service.is_resident(SHUTDOWN), False)
    check("重启是系统级", action_service.is_resident(RESTART), False)
    check("未知动作非法", action_service.is_valid("bogus"), False)

    outcome = action_service.arm(LOCK, 3600)
    check("锁定下发不执行命令", (outcome.ok, outcome.deferred), (True, True))
    outcome = action_service.arm(HIBERNATE, 7200)
    check("休眠下发不执行命令", (outcome.ok, outcome.deferred), (True, True))
    outcome = action_service.cancel(LOCK)
    check("锁定取消走内部清理", (outcome.ok, outcome.deferred), (True, True))

    outcome = action_service.arm(RESTART, 0)
    check("重启非法秒数被拒（不真实下发）", outcome.ok, False)
    outcome = action_service.arm("bogus", 60)
    check("未知动作被拒", outcome.ok, False)

    result = shutdown_service.arm(60, mode="x")
    check("shutdown 未知模式被拒", result.ok, False)

    print("主题色：")
    check("关机橙", styles.theme_accent("shutdown"), "#F25C34")
    check("重启蓝", styles.theme_accent("restart"), "#2F80ED")
    check("锁定紫", styles.theme_accent("lock"), "#7C5CFC")
    check("休眠青", styles.theme_accent("hibernate"), "#00A3A3")
    check("未知模式回退关机", styles.theme_accent("bogus"), "#F25C34")

    for action, color in (
        ("shutdown", "#F25C34"),
        ("restart", "#2F80ED"),
        ("lock", "#7C5CFC"),
        ("hibernate", "#00A3A3"),
    ):
        check(f"build_qss 含 {action} 主题色", color in styles.build_qss(action), True)

    print("控件联动：")
    dial = ClockDial()
    dial.set_accent("#2F80ED")
    check("表盘中心点变色", dial._accent, "#2F80ED")  # noqa: SLF001

    toggle = ToggleSwitch(True)
    toggle.set_on_color("#7C5CFC")
    check("开关轨道变色", toggle._on_color, "#7C5CFC")  # noqa: SLF001

    print("计划与设置的动作字段：")
    plan_tmp = Path(tempfile.gettempdir()) / "ss_test_actions_plan.json"
    plan_tmp.unlink(missing_ok=True)
    plan_store = PlanStore(plan_tmp)
    from datetime import datetime, timedelta

    now = datetime.now()
    plan_store.save(
        __import__("core.plan_store", fromlist=["Plan"]).Plan(
            target_ts=(now + timedelta(hours=1)).timestamp(),
            target_text="test",
            created_ts=now.timestamp(),
            seconds=3600,
            source="dial",
            action=LOCK,
        )
    )
    restored = plan_store.load()
    check("计划记住动作类型", restored.action if restored else None, LOCK)

    # 旧格式记录（无 action 字段）回退为关机
    raw = json.loads(plan_tmp.read_text(encoding="utf-8"))
    raw.pop("action", None)
    plan_tmp.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    legacy = plan_store.load()
    check("旧记录回退为关机", legacy.action if legacy else None, SHUTDOWN)
    plan_tmp.unlink(missing_ok=True)

    settings_tmp = Path(tempfile.gettempdir()) / "ss_test_actions_settings.json"
    settings_tmp.unlink(missing_ok=True)
    settings_store = SettingsStore(settings_tmp)
    settings_store.save(Settings(action=HIBERNATE))
    check("设置往返动作类型", settings_store.load().action, HIBERNATE)
    settings_tmp.write_text('{"version":1,"action":"bogus"}', encoding="utf-8")
    check("非法动作回退关机", settings_store.load().action, SHUTDOWN)
    settings_tmp.unlink(missing_ok=True)

    print(f"\n通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
