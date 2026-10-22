"""Windows shutdown 命令封装。

这是整个项目里**唯一**允许调用 shutdown 的地方（见 docs/02-技术方案.md §3）。

对应需求：FR-06（设定）、FR-07（返回码）、FR-08（取消）。
"""

from __future__ import annotations

import locale
import logging
import subprocess
from dataclasses import dataclass

from core.clock_math import MAX_SECONDS, MIN_SECONDS

LOGGER = logging.getLogger(__name__)

# 返回码说明。集中在此处，界面层通过 describe() 取用。
CODE_MESSAGES: dict[int, str] = {
    0: "操作成功",
    5: "拒绝访问，请以管理员身份运行",
    1116: "当前没有待执行的关机计划",
    1190: "已存在关机计划，请先取消",
}

# 内部错误码（非系统返回）
CODE_BAD_INPUT = -2
CODE_CMD_FAILED = -1


@dataclass(frozen=True)
class Result:
    """一次 shutdown 调用的结果。"""

    ok: bool
    code: int
    message: str
    output: str = ""
    """系统原始输出，供排错时显示。"""


def describe(code: int) -> str:
    """把返回码翻译成中文说明。"""
    return CODE_MESSAGES.get(code, f"系统返回错误码 {code}")


def arm(seconds: int, mode: str = "s") -> Result:
    """下发计划：shutdown /<mode> /t <seconds>。

    mode: "s" 关机，"r" 重启（两种都支持系统级定时）。
    刻意不传 /f：强制关闭应用会导致数据丢失。
    """
    if mode not in ("s", "r"):
        return Result(False, CODE_BAD_INPUT, f"未知的 shutdown 模式 {mode!r}", "")
    if not isinstance(seconds, int):
        return Result(False, CODE_BAD_INPUT, "秒数必须为整数", "")
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        return Result(
            False,
            CODE_BAD_INPUT,
            f"秒数超出允许范围（{MIN_SECONDS} ~ {MAX_SECONDS}）",
            "",
        )

    code, output = _run(f"/{mode}", "/t", str(seconds))
    return _to_result(code, output)


def cancel() -> Result:
    """取消待定关机：shutdown /a。"""
    code, output = _run("/a")
    return _to_result(code, output)


# ---------------------------------------------------------------------------


def _run(*args: str) -> tuple[int, str]:
    command = ["shutdown", *args]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            timeout=15,
            # 不弹控制台黑框
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        LOGGER.error("shutdown 执行超时：%s", command)
        return CODE_CMD_FAILED, "命令执行超时"
    except OSError as exc:
        LOGGER.exception("无法执行 shutdown：%s", exc)
        return CODE_CMD_FAILED, str(exc)

    output = (_decode(proc.stdout) + _decode(proc.stderr)).strip()
    LOGGER.info(
        "shutdown %s -> 返回码 %s，输出 %r",
        " ".join(args),
        proc.returncode,
        output,
    )
    return proc.returncode, output


def _decode(data: bytes) -> str:
    """shutdown 的输出是系统 OEM 编码，中文系统下为 GBK，不能用 UTF-8。"""
    if not data:
        return ""
    for encoding in (locale.getpreferredencoding(False), "mbcs", "utf-8"):
        try:
            return data.decode(encoding).strip()
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace").strip()


def _to_result(code: int, output: str) -> Result:
    return Result(ok=code == 0, code=code, message=describe(code), output=output)
