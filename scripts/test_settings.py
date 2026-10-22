"""V1.1 阶段 1 回归：设置持久化、开机自启、关窗行为、设置/询问对话框。

不涉及真实关机计划；自启测试会临时写注册表，但前后都记录并恢复原值。

运行：.venv\\Scripts\\python.exe scripts\\test_settings.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import winreg
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtGui import QCloseEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

from core import autostart  # noqa: E402
from core.settings import (  # noqa: E402
    CLOSE_ASK,
    CLOSE_EXIT,
    CLOSE_TRAY,
    Settings,
    SettingsStore,
)
from ui import strings  # noqa: E402
from ui.close_choice_dialog import CloseChoiceDialog  # noqa: E402
from ui.controls import CheckBox  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.settings_dialog import SettingsDialog  # noqa: E402

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


def read_autostart_raw():
    try:
        with autostart._open_key(write=False) as key:  # noqa: SLF001
            return winreg.QueryValueEx(key, autostart.VALUE_NAME)[0]
    except FileNotFoundError:
        return None


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # ---- 设置持久化 ----
    tmp_path = Path(tempfile.gettempdir()) / "ss_test_settings.json"
    tmp_path.unlink(missing_ok=True)
    store = SettingsStore(tmp_path)

    print("设置持久化：")
    check("文件不存在时用默认值", store.load(), Settings())
    store.save(Settings(autostart=True, tray_countdown=False, close_action=CLOSE_TRAY))
    loaded = store.load()
    check("往返一致", (loaded.autostart, loaded.tray_countdown, loaded.close_action), (True, False, CLOSE_TRAY))

    tmp_path.write_text("{坏掉的 json", encoding="utf-8")
    check("损坏文件回退默认值", store.load(), Settings())

    tmp_path.write_text('{"version":1,"close_action":"乱写"}', encoding="utf-8")
    check("非法关窗行为回退为每次询问", store.load().close_action, CLOSE_ASK)
    tmp_path.unlink(missing_ok=True)

    # ---- 开机自启 ----
    print("开机自启（临时写注册表，结束后恢复原值）：")
    original = read_autostart_raw()
    test_target = '"C:\\Windows\\System32\\notepad.exe" --test'
    try:
        autostart.disable()
        check("初始未开启", autostart.is_enabled(), False)

        check("enable 成功", autostart.enable(test_target), True)
        check("开启后可查到", autostart.is_enabled(), True)
        check("值等于目标命令", autostart.is_enabled(test_target), True)
        check("值不同时视为未开启", autostart.is_enabled('"别的.exe"'), False)

        check("disable 成功", autostart.disable(), True)
        check("关闭后查不到", autostart.is_enabled(), False)
    finally:
        if original is None:
            autostart.disable()
        else:
            autostart.enable(original)
    print(f"       已恢复原值：{'（原本没有）' if original is None else original}")

    # ---- 设置对话框 ----
    print("设置对话框：")
    dialog = SettingsDialog(Settings(autostart=True, close_action=CLOSE_EXIT))
    result = dialog.result()
    check("回显开机自启", result.autostart, True)
    check("回显关窗行为", result.close_action, CLOSE_EXIT)

    dialog._autostart_toggle.set_checked(False)  # noqa: SLF001
    dialog._tray_toggle.set_checked(False)  # noqa: SLF001
    ask_index = [CLOSE_ASK, CLOSE_TRAY, CLOSE_EXIT].index(CLOSE_ASK)
    dialog._close_segment.set_current(ask_index)  # noqa: SLF001
    updated = dialog.result()
    check("改选每次询问", updated.close_action, CLOSE_ASK)
    check("改掉托盘倒计时", updated.tray_countdown, False)
    check("改掉开机自启", updated.autostart, False)

    # ---- 关窗询问 ----
    print("关窗询问：")
    choice_dialog = CloseChoiceDialog()
    tray_button = next(
        b for b in choice_dialog.findChildren(QPushButton)
        if b.text() == strings.DLG_CLOSE_BTN_TRAY
    )
    tray_button.click()
    check("点托盘按钮返回 tray", choice_dialog.result(), ("tray", False))

    choice_dialog = CloseChoiceDialog()
    checkbox = choice_dialog.findChildren(CheckBox)[0]
    checkbox.set_checked(True)
    exit_button = next(
        b for b in choice_dialog.findChildren(QPushButton)
        if b.text() == strings.DLG_CLOSE_BTN_EXIT
    )
    exit_button.click()
    check("勾选不再显示 + 退出", choice_dialog.result(), ("exit", True))

    # ---- closeEvent 三种行为 ----
    print("closeEvent 三种关窗行为：")
    plan_tmp = Path(tempfile.gettempdir()) / "ss_test_close.json"
    plan_tmp.unlink(missing_ok=True)
    settings_tmp = Path(tempfile.gettempdir()) / "ss_test_close_settings.json"
    settings_tmp.unlink(missing_ok=True)

    window = MainWindow(
        store=__import__("core.plan_store", fromlist=["PlanStore"]).PlanStore(plan_tmp),
        settings_store=SettingsStore(settings_tmp),
        enable_tray=False,
    )

    window._apply_settings(Settings(close_action=CLOSE_EXIT))
    event = QCloseEvent()
    window.closeEvent(event)
    check("设为总是退出 → 接受关闭", event.isAccepted(), True)

    window._apply_settings(Settings(close_action=CLOSE_TRAY))
    window.show()
    event = QCloseEvent()
    window.closeEvent(event)
    check("设为总是托盘 → 拒绝关闭", event.isAccepted(), False)
    check("窗口已隐藏", window.isVisible(), False)

    # ask 模式：mock 掉对话框，模拟选托盘 + 记住
    import ui.main_window as main_window_module

    original_dialog = main_window_module.CloseChoiceDialog

    class FakeDialog(original_dialog):  # type: ignore[misc, valid-type]
        def exec(self):
            self._finish("tray", True)
            return 1

    main_window_module.CloseChoiceDialog = FakeDialog
    try:
        window._apply_settings(Settings(close_action=CLOSE_ASK))
        event = QCloseEvent()
        window.closeEvent(event)
        check("ask 模式选托盘 → 拒绝关闭", event.isAccepted(), False)
        check("记住选择已写入", window._settings.close_action, CLOSE_TRAY)
    finally:
        main_window_module.CloseChoiceDialog = original_dialog

    window.close()
    plan_tmp.unlink(missing_ok=True)
    settings_tmp.unlink(missing_ok=True)

    print(f"\n通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    raise SystemExit(main())
