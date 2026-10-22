"""P1 自测：关机指令层的设定 / 记录 / 取消 / 复核。

安全说明
--------
1. 倒计时固定 600 秒（10 分钟），远大于任何一次自测耗时。
2. 无论中间哪一步失败，`finally` 都会再执行一次取消做兜底。
3. 全程不使用 /f。

运行：.venv\\Scripts\\python.exe scripts\\selftest_shutdown.py
或双击 scripts\\selftest.bat
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from core import shutdown_service  # noqa: E402
from core.plan_store import Plan, PlanStore  # noqa: E402

TEST_SECONDS = 600
TOTAL_STEPS = 5

_state = {"passed": 0, "failed": 0}


def step(index: int, name: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    if ok:
        _state["passed"] += 1
    else:
        _state["failed"] += 1
    line = f"[{mark}] {index}/{TOTAL_STEPS} {name}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return ok


def main() -> int:
    store = PlanStore()

    print("=" * 58)
    print(" 关机指令层自测 · 倒计时 600 秒（10 分钟）")
    print(f" 记录文件：{store.path}")
    print("=" * 58)

    existing = store.load()
    if existing is not None:
        print(f"\n检测到已有计划（{existing.target_text}），为避免叠加，测试中止。")
        print("请先在软件中取消该计划，或手动执行：shutdown /a")
        return 2

    try:
        # 1. 下发
        result = shutdown_service.arm(TEST_SECONDS)
        step(1, "下发 600 秒关机计划", result.ok, f"返回码 {result.code}")

        # 2. 写入本地记录并读回
        now = datetime.now()
        target = now + timedelta(seconds=TEST_SECONDS)
        plan = Plan(
            target_ts=target.timestamp(),
            target_text=target.strftime("%Y-%m-%d %H:%M"),
            created_ts=now.timestamp(),
            seconds=TEST_SECONDS,
            source="preset",
        )
        store.save(plan)
        loaded = store.load()
        same = loaded is not None and abs(loaded.target_ts - plan.target_ts) < 1
        step(2, "本地记录写入与读回一致", same, loaded.target_text if loaded else "读回为空")

        # 3. 取消
        cancelled = shutdown_service.cancel()
        step(3, "取消关机计划", cancelled.ok, f"返回码 {cancelled.code}")

        # 4. 清除记录
        store.clear()
        step(4, "清除本地记录", store.load() is None)

        # 5. 再次取消，应返回 1116 证明系统里确实没有计划
        again = shutdown_service.cancel()
        step(
            5,
            "复核系统无待定关机",
            again.code == 1116,
            f"返回码 {again.code} {again.message}",
        )

    finally:
        # 兜底：任何异常路径下都再取消一次
        shutdown_service.cancel()
        store.clear()

    print("-" * 58)
    if _state["failed"] == 0:
        print(f"全部通过（{_state['passed']}/{TOTAL_STEPS}）· 当前系统无待定关机")
        return 0

    print(f"失败 {_state['failed']} 项（通过 {_state['passed']}/{TOTAL_STEPS}）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
