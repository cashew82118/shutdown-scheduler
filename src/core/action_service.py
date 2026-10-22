"""动作分发：把「动作类型」翻译成具体执行方式。

四种动作两条通道（见 docs/01 §5.5）：
- 关机 / 重启：`shutdown /s|/r /t N`，系统级，程序退出不影响
- 锁定 / 休眠：Windows 没有系统级定时，由常驻程序到点执行，
  进程被杀或电脑重启即失效（退出时强警告兜底）

对应需求 FR-13。
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

from core import shutdown_service

LOGGER = logging.getLogger(__name__)

SHUTDOWN = "shutdown"
RESTART = "restart"
LOCK = "lock"
HIBERNATE = "hibernate"

ACTIONS = (SHUTDOWN, RESTART, LOCK, HIBERNATE)
SYSTEM_ACTIONS = (SHUTDOWN, RESTART)
RESIDENT_ACTIONS = (LOCK, HIBERNATE)


def is_valid(action: str) -> bool:
    return action in ACTIONS


def is_resident(action: str) -> bool:
    """该动作是否依赖程序常驻。"""
    return action in RESIDENT_ACTIONS


@dataclass(frozen=True)
class ArmOutcome:
    """arm 的统一结果：系统级走 shutdown_service 的 Result，常驻则标记 deferred。"""

    ok: bool
    code: int
    message: str
    deferred: bool
    """True 表示计划由本进程到点执行（不经过 shutdown 计时器）。"""


def arm(action: str, seconds: int) -> ArmOutcome:
    if action == SHUTDOWN:
        result = shutdown_service.arm(seconds, mode="s")
        return ArmOutcome(result.ok, result.code, result.message, deferred=False)
    if action == RESTART:
        result = shutdown_service.arm(seconds, mode="r")
        return ArmOutcome(result.ok, result.code, result.message, deferred=False)
    if action in RESIDENT_ACTIONS:
        # 参数校验与 shutdown 共用同一组边界
        from core.clock_math import MAX_SECONDS, MIN_SECONDS

        if not MIN_SECONDS <= seconds <= MAX_SECONDS:
            return ArmOutcome(
                False,
                shutdown_service.CODE_BAD_INPUT,
                f"秒数超出允许范围（{MIN_SECONDS} ~ {MAX_SECONDS}）",
                deferred=False,
            )
        # 常驻动作不需要在这里执行任何命令：主窗口的 QTimer 到点调 execute_now
        return ArmOutcome(True, 0, "已交由程序常驻执行", deferred=True)

    return ArmOutcome(False, shutdown_service.CODE_BAD_INPUT, f"未知动作 {action!r}", deferred=False)


def cancel(action: str) -> ArmOutcome:
    if action in SYSTEM_ACTIONS:
        result = shutdown_service.cancel()
        return ArmOutcome(result.ok, result.code, result.message, deferred=False)
    if action in RESIDENT_ACTIONS:
        return ArmOutcome(True, 0, "已清除常驻计划", deferred=True)
    return ArmOutcome(False, shutdown_service.CODE_BAD_INPUT, f"未知动作 {action!r}", deferred=False)


def execute_now(action: str) -> bool:
    """到点立即执行常驻动作。关机/重启不走这里（已经是系统级）。"""
    if action == LOCK:
        command = ["rundll32", "user32.dll,LockWorkStation"]
    elif action == HIBERNATE:
        command = ["shutdown", "/h"]
    else:
        LOGGER.warning("execute_now 收到不该出现的动作：%s", action)
        return False

    try:
        subprocess.run(
            command,
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        LOGGER.info("常驻动作已执行：%s", action)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        LOGGER.exception("常驻动作执行失败 %s：%s", action, exc)
        return False
