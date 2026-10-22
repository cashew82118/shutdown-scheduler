"""运行时资源路径解析。

开发期指向项目 assets/，打包后指向 PyInstaller 解包目录（sys._MEIPASS）。
因此 build.bat 必须带 `--add-data "assets;assets"`。
"""

from __future__ import annotations

import sys
from pathlib import Path


def assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        # --add-data "assets;assets" 保留了目录结构，资源在 _MEIPASS/assets/ 下
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


def icon_path() -> Path:
    return assets_dir() / "app.ico"
