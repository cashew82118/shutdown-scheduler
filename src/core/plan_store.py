"""本地关机计划记录。

Windows 没有公开接口查询「当前是否存在待定关机」，因此以本文件为准
（限制说明见 docs/01-需求规格.md §5.3）。

对应需求：FR-07（查询）、FR-08（取消后清除）。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger(__name__)

STATE_VERSION = 1
APP_DIR_NAME = "ShutdownScheduler"
STATE_FILE_NAME = "state.json"

VALID_SOURCES = ("dial", "wheel", "preset")
VALID_ACTIONS = ("shutdown", "restart", "lock", "hibernate")


@dataclass(frozen=True)
class Plan:
    """一条已下发到系统的关机计划。"""

    target_ts: float
    """目标时刻的时间戳（秒）。"""

    target_text: str
    """目标时刻的可读文本，如 2026-10-22 07:30。"""

    created_ts: float
    """下发时间的时间戳。"""

    seconds: int
    """下发时传给 shutdown /t 的秒数。"""

    source: str
    """来源：dial（表盘）/ wheel（轮盘）/ preset（预设按钮）。"""

    action: str = "shutdown"
    """动作类型：shutdown / restart / lock / hibernate。旧记录回退为关机。"""

    @property
    def target_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.target_ts)

    @property
    def created_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.created_ts)


def default_state_path() -> Path:
    """%LOCALAPPDATA%\\ShutdownScheduler\\state.json"""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / APP_DIR_NAME / STATE_FILE_NAME


class PlanStore:
    """计划记录的读写。所有异常都在内部消化，不让界面层崩。"""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else default_state_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self, now: datetime | None = None) -> Plan | None:
        """读取计划；不存在、损坏或已过期时返回 None。

        过期记录会被顺带清除。
        """
        if not self._path.exists():
            return None

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("计划记录读取失败，按无计划处理：%s", exc)
            self.clear()
            return None

        plan = self._to_plan(raw)
        if plan is None:
            LOGGER.warning("计划记录格式不正确，已丢弃")
            self.clear()
            return None

        current = now if now is not None else datetime.now()
        if plan.target_ts <= current.timestamp():
            LOGGER.info("计划已过期（目标 %s），清除记录", plan.target_text)
            self.clear()
            return None

        return plan

    def save(self, plan: Plan) -> None:
        """原子写入，避免写一半断电留下坏文件。"""
        payload = {"version": STATE_VERSION, **asdict(plan)}
        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, self._path)
        LOGGER.info("计划已记录：%s（%s 秒，来源 %s）", plan.target_text, plan.seconds, plan.source)

    def clear(self) -> None:
        try:
            self._path.unlink(missing_ok=True)
        except OSError as exc:
            LOGGER.warning("清除计划记录失败：%s", exc)

    @staticmethod
    def _to_plan(raw: object) -> Plan | None:
        if not isinstance(raw, dict):
            return None
        if raw.get("version") != STATE_VERSION:
            return None

        try:
            target_ts = float(raw["target_ts"])
            created_ts = float(raw["created_ts"])
            seconds = int(raw["seconds"])
            target_text = str(raw["target_text"])
            source = str(raw.get("source", "dial"))
            action = str(raw.get("action", "shutdown"))
        except (KeyError, TypeError, ValueError):
            return None

        if source not in VALID_SOURCES:
            source = "dial"
        if action not in VALID_ACTIONS:
            action = "shutdown"

        return Plan(
            target_ts=target_ts,
            target_text=target_text,
            created_ts=created_ts,
            seconds=seconds,
            source=source,
            action=action,
        )
