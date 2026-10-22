"""开机自启：注册表 HKCU\\...\\Run 的单键读写。

只碰当前用户的一个键，不写服务、不建计划任务（NFR-04）。
键名固定为 ShutdownScheduler，值写入 exe 完整路径。

注意：Windows 用 sz 类型字符串，必须用 winreg.REG_SZ。
"""

from __future__ import annotations

import logging
import winreg
from pathlib import Path

LOGGER = logging.getLogger(__name__)

KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ShutdownScheduler"


def _open_key(write: bool) -> winreg.HKEYType:
    access = winreg.KEY_READ if not write else winreg.KEY_SET_VALUE
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH, 0, access)


def is_enabled(target: str | None = None) -> bool:
    """已开启且（给了 target 时）值与当前启动命令一致。"""
    try:
        with _open_key(write=False) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return False
    except OSError as exc:
        LOGGER.warning("读取自启键失败：%s", exc)
        return False

    if not isinstance(value, str):
        return False
    if target is None:
        return bool(value)
    return value.strip() == target.strip()


def enable(target: str) -> bool:
    """写入 Run 键。target 可以是带引号和参数的命令行。返回是否成功。"""
    try:
        with _open_key(write=True) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, target)
    except OSError as exc:
        LOGGER.exception("写入自启键失败：%s", exc)
        return False

    LOGGER.info("开机自启已开启：%s", target)
    return True


def disable() -> bool:
    """删除 Run 键（不存在也算成功）。"""
    try:
        with _open_key(write=True) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        return True
    except OSError as exc:
        LOGGER.exception("删除自启键失败：%s", exc)
        return False

    LOGGER.info("开机自启已关闭")
    return True
