"""用户设置持久化。

对应需求：FR-10（关窗行为）、FR-11（开机自启）、FR-12（托盘倒计时）。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)

APP_DIR_NAME = "ShutdownScheduler"
SETTINGS_FILE_NAME = "settings.json"
SETTINGS_VERSION = 1

CLOSE_ASK = "ask"
CLOSE_TRAY = "tray"
CLOSE_EXIT = "exit"
CLOSE_ACTIONS = (CLOSE_ASK, CLOSE_TRAY, CLOSE_EXIT)


@dataclass(frozen=True)
class Settings:
    """全部默认值即产品默认行为，改这里就等于改产品默认值。"""

    autostart: bool = False
    tray_countdown: bool = True
    close_action: str = CLOSE_ASK
    action: str = "shutdown"


def default_settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / APP_DIR_NAME / SETTINGS_FILE_NAME


class SettingsStore:
    """设置的读写。任何异常都降级为默认值，不让界面层崩。"""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else default_settings_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("设置读取失败，使用默认值：%s", exc)
            return Settings()

        return self._to_settings(raw)

    def save(self, settings: Settings) -> None:
        payload = {"version": SETTINGS_VERSION, **asdict(settings)}
        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, self._path)
        LOGGER.info("设置已保存：%s", payload)

    @staticmethod
    def _to_settings(raw: object) -> Settings:
        default = Settings()
        if not isinstance(raw, dict):
            return default

        close_action = raw.get("close_action", default.close_action)
        if close_action not in CLOSE_ACTIONS:
            LOGGER.warning("未知的关窗行为 %r，回退为每次询问", close_action)
            close_action = CLOSE_ASK

        action = raw.get("action", default.action)
        if action not in ("shutdown", "restart", "lock", "hibernate"):
            LOGGER.warning("未知动作类型 %r，回退为关机", action)
            action = "shutdown"

        return Settings(
            autostart=bool(raw.get("autostart", default.autostart)),
            tray_countdown=bool(raw.get("tray_countdown", default.tray_countdown)),
            close_action=close_action,
            action=action,
        )
