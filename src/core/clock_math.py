"""时间计算。

纯函数模块：把「几点几分」换算成目标时刻与剩余秒数，不做任何 IO、
不依赖 UI、不调用系统命令，因此可以脱离窗口单独验证。

对应需求：FR-04（跨天判定）、FR-06（秒数边界）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# shutdown /t 的取值范围
MIN_SECONDS = 60
MAX_SECONDS = 315_360_000  # 约 10 年，Windows 允许的上限


@dataclass(frozen=True)
class Target:
    """一次选时的解析结果。"""

    moment: datetime
    """实际执行关机的绝对时刻。"""

    is_next_day: bool
    """相对当前日期是否落在明天，界面需据此显示「明天」。"""


def resolve_target(now: datetime, hour: int, minute: int) -> Target:
    """把 (时, 分) 解析成目标时刻。

    规则（见 docs/01-需求规格.md FR-04）：
    选中的时刻距现在已经不足 MIN_SECONDS 秒时，视为「已过」，顺延到明天。
    """
    if not 0 <= hour <= 23:
        raise ValueError(f"hour 必须在 0..23，收到 {hour}")
    if not 0 <= minute <= 59:
        raise ValueError(f"minute 必须在 0..59，收到 {minute}")

    moment = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if (moment - now).total_seconds() < MIN_SECONDS:
        moment += timedelta(days=1)
        return Target(moment=moment, is_next_day=True)
    return Target(moment=moment, is_next_day=False)


def seconds_until(moment: datetime, now: datetime) -> int:
    """剩余秒数，向下取整并夹到 shutdown 的合法区间。"""
    delta = int((moment - now).total_seconds())
    if delta < MIN_SECONDS:
        return MIN_SECONDS
    if delta > MAX_SECONDS:
        return MAX_SECONDS
    return delta


def is_expired(moment: datetime, now: datetime) -> bool:
    """目标时刻是否已过（用于清理本地记录）。"""
    return moment <= now


# ---------------------------------------------------------------------------
# 内置自测：python src/core/clock_math.py
# ---------------------------------------------------------------------------


def _self_check() -> int:
    failures = 0

    def check(name: str, actual, expected) -> None:
        nonlocal failures
        if actual == expected:
            print(f"  PASS  {name}")
        else:
            failures += 1
            print(f"  FAIL  {name}: 期望 {expected!r}，实际 {actual!r}")

    base = datetime(2026, 10, 21, 20, 0, 0)

    t = resolve_target(base, 20, 1)
    check("恰好 60 秒算今天", (t.is_next_day, t.moment), (False, datetime(2026, 10, 21, 20, 1)))
    check("恰好 60 秒的剩余", seconds_until(t.moment, base), 60)

    t = resolve_target(base, 20, 0)
    check("选当前时刻顺延到明天", (t.is_next_day, t.moment), (True, datetime(2026, 10, 22, 20, 0)))

    t = resolve_target(datetime(2026, 10, 21, 20, 0, 30), 20, 1)
    check("不足 60 秒顺延到明天", t.is_next_day, True)

    t = resolve_target(base, 19, 59)
    check("早于当前时刻顺延到明天", (t.is_next_day, t.moment), (True, datetime(2026, 10, 22, 19, 59)))

    t = resolve_target(base, 23, 59)
    check("23:59 属今天", t.is_next_day, False)
    check("23:59 的剩余秒数", seconds_until(t.moment, base), 3 * 3600 + 59 * 60)

    t = resolve_target(datetime(2026, 10, 21, 23, 59, 0), 23, 58)
    check("跨午夜顺延", t.moment, datetime(2026, 10, 22, 23, 58))

    check("过期判定-已过", is_expired(datetime(2026, 10, 21, 19, 0), base), True)
    check("过期判定-未到", is_expired(datetime(2026, 10, 21, 21, 0), base), False)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_self_check())
