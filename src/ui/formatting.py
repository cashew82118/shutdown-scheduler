"""展示层格式化函数。

放在这里而不是散落在界面代码里，便于单独验证。
"""

from __future__ import annotations

from datetime import datetime

from ui import strings


def format_clock(hour: int, minute: int) -> str:
    """20:30"""
    return f"{hour:02d}:{minute:02d}"


def format_when(target: datetime, now: datetime) -> str:
    """今天 20:30 / 明天 07:05"""
    day = strings.DAY_TOMORROW if target.date() != now.date() else strings.DAY_TODAY
    return f"{day} {target.hour:02d}:{target.minute:02d}"


def format_remaining(total_seconds: int) -> str:
    """11 小时 28 分 3 秒（省略为 0 的高位）"""
    if total_seconds <= 0:
        return "0 秒"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if hours:
        parts.append(f"{hours} 小时")
    if minutes:
        parts.append(f"{minutes} 分")
    if seconds or not parts:
        parts.append(f"{seconds} 秒")
    return " ".join(parts)
