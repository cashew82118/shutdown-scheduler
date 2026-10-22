"""调色板、尺寸常量与 QSS。

所有色值与尺寸的唯一来源，取值依据见 docs/03-设计规范.md。
界面代码不得自行硬编码颜色。
"""

# --- 基础色 ---
BG = "#F4F5F7"
SURFACE = "#FFFFFF"
BORDER = "#E3E6EB"
TEXT = "#1B1F27"
TEXT_SUB = "#7A828F"
TEXT_DISABLED = "#B6BCC6"
ACCENT = "#F25C34"
ACCENT_HOVER = "#E24E27"
ACCENT_PRESS = "#C9421F"

# 每种动作的主题色：主色 / hover / press（FR-14）
THEMES: dict[str, tuple[str, str, str]] = {
    "shutdown": ("#F25C34", "#E24E27", "#C9421F"),
    "restart": ("#2F80ED", "#1F6FD6", "#1A5EB8"),
    "lock": ("#7C5CFC", "#6B4BE0", "#5A3EC8"),
    "hibernate": ("#00A3A3", "#008C8C", "#007575"),
}


def theme_colors(action: str) -> tuple[str, str, str]:
    """返回 (主色, hover, press)。未知动作回退为关机橙。"""
    return THEMES.get(action, THEMES["shutdown"])


def theme_accent(action: str) -> str:
    return theme_colors(action)[0]
DANGER = "#D93B2B"
OK = "#2E9A6B"

# --- 表盘色 ---
DIAL_BG = "#1F2430"
DIAL_BG_INNER = "#262C3A"
TICK_MINOR = "#3A4254"
TICK_MAJOR = "#6B7688"
DIAL_NUM = "#9AA3B2"
HAND = "#FFFFFF"

# --- 字体与尺寸 ---
FONT_FAMILY = '"Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif'

WINDOW_WIDTH = 460
WINDOW_HEIGHT = 718
PADDING_X = 24
PADDING_Y = 20

DIAL_SIZE = 280
WHEEL_HEIGHT = 132
WHEEL_ROW_HEIGHT = 44

PRESET_HEIGHT = 36
PRIMARY_HEIGHT = 46
SECONDARY_HEIGHT = 36
STATUS_HEIGHT = 38

# --- 全局样式 ---


def build_qss(action: str = "shutdown") -> str:
    """生成整套 QSS，主色随动作模式变化。"""
    accent, accent_hover, accent_press = theme_colors(action)
    return f"""
QWidget#Root {{
    background-color: {BG};
}}
QLabel {{
    font-family: {FONT_FAMILY};
    color: {TEXT};
}}
QLabel#Clock {{
    font-size: 32px;
    font-weight: 600;
    color: {TEXT};
}}
QLabel#Day {{
    font-size: 13px;
    color: {TEXT_SUB};
}}
QLabel#Hint {{
    font-size: 12px;
    color: {TEXT_DISABLED};
}}
QLabel#Version {{
    font-size: 11px;
    color: {TEXT_DISABLED};
}}

QPushButton {{
    font-family: {FONT_FAMILY};
}}
QPushButton#Preset {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    color: {TEXT};
    font-size: 13px;
}}
QPushButton#Preset:hover {{
    background-color: #F9FAFB;
}}
QPushButton#Preset:pressed {{
    background-color: #F0F2F5;
}}

QPushButton#Primary {{
    background-color: {accent};
    border: none;
    border-radius: 12px;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background-color: {accent_hover};
}}
QPushButton#Primary:pressed {{
    background-color: {accent_press};
}}
QPushButton#Primary:disabled {{
    background-color: {BORDER};
    color: {TEXT_DISABLED};
}}

QPushButton#Secondary {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    color: {TEXT};
    font-size: 14px;
}}
QPushButton#Secondary:hover {{
    border-color: {DANGER};
    color: {DANGER};
}}
QPushButton#Secondary:disabled {{
    color: {TEXT_DISABLED};
    border-color: #EFF1F4;
}}

QFrame#StatusBar {{
    background-color: #F9FAFB;
    border-radius: 10px;
}}
QLabel#StatusText {{
    font-size: 12px;
    color: {TEXT_SUB};
}}

QPushButton#IconButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {TEXT_SUB};
    font-size: 15px;
    padding: 2px 8px;
}}
QPushButton#IconButton:hover {{
    background-color: #E9ECF1;
    color: {TEXT};
}}

QLabel#ModeHint {{
    font-size: 12px;
    color: {TEXT_SUB};
}}
QLabel#SettingLabel {{
    font-size: 13px;
    color: {TEXT};
}}
QLabel#SettingHint {{
    font-size: 11px;
    color: {TEXT_DISABLED};
}}
QLabel#SettingGroup {{
    font-size: 12px;
    color: {TEXT_SUB};
}}
"""


# 兼容旧引用：默认主题（关机橙）
APP_QSS = build_qss("shutdown")
