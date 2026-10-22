"""集中管理界面文案。

规则（见 docs/03-设计规范.md §6.1）：界面代码中不得出现中文字面量，
所有对用户可见的文字都必须从这里取。
"""

# --- 窗口 ---
APP_TITLE = "定时关机"
APP_VERSION = "1.1.0"

# --- 顶部选中时间 ---
DAY_TODAY = "今天"
DAY_TOMORROW = "明天"

# --- 状态条 ---
STATUS_NONE = "当前无计划"
STATUS_PLANNED = "将于 {when} {mode} · 剩余 {remaining}"
STATUS_RESIDENT_HINT = "（需保持程序运行）"

# --- 按钮 ---
BTN_SET = "设定关机"
BTN_CANCEL = "取消计划"

# (显示文字, 分钟数)
PRESET_BUTTONS: tuple[tuple[str, int], ...] = (
    ("30 分", 30),
    ("1 小时", 60),
    ("2 小时", 120),
    ("3 小时", 180),
)

# --- 对话框 ---
DLG_OVERWRITE_TITLE = "覆盖已有计划"
DLG_OVERWRITE_TEXT = "当前已有计划将在 {when} 关机。\n\n是否用新的时间替换它？"

DLG_EXTERNAL_TITLE = "发现其他来源的计划"
DLG_EXTERNAL_TEXT = (
    "系统中已存在一个关机计划，但它不是本软件设定的，无法读取具体时间。\n\n"
    "是否取消它，改为在 {when} 关机？"
)

DLG_CANCEL_TITLE = "取消关机计划"
DLG_CANCEL_TEXT = "确定取消 {when} 的关机计划吗？"

BTN_CONFIRM = "确定"
BTN_DISMISS = "再想想"

# --- 提示与错误 ---
MSG_CANCELLED = "已取消关机计划"
ERR_SET_FAILED = "设定失败：{message}"
ERR_CANCEL_FAILED = "取消失败：{message}"
ERR_REPLACED_FAILED = "设定失败：{message}（原计划已取消）"
ERR_TOO_SOON = "距离现在不足 1 分钟，请选择更晚的时间"

# --- 表盘 / 轮盘 ---
DIAL_HINT_DRAG = "拖指针调时间，点空白处快速定位"

# --- 托盘（v1.1）---
TRAY_SHOW = "显示主窗口"
TRAY_SETTINGS = "设置"
TRAY_QUIT = "退出"
TRAY_TOOLTIP = "定时关机"
TRAY_TOOLTIP_HINT = "双击恢复窗口"

# --- 关窗询问（v1.1）---
DLG_CLOSE_TITLE = "关闭窗口"
DLG_CLOSE_TEXT = (
    "要把窗口最小化到托盘，还是直接退出程序？\n\n"
    "最小化到托盘后，关机计划继续有效，双击托盘图标即可恢复窗口。"
)
DLG_CLOSE_BTN_TRAY = "最小化到托盘"
DLG_CLOSE_BTN_EXIT = "退出程序"
DLG_CLOSE_REMEMBER = "不再显示"

# --- 设置窗（v1.1）---
SETTINGS_TITLE = "设置"
SETTINGS_AUTOSTART = "开机自动启动"
SETTINGS_AUTOSTART_HINT = "开机后在托盘待命，不会弹出窗口"
SETTINGS_TRAY_COUNTDOWN = "托盘显示剩余时间"
SETTINGS_TRAY_COUNTDOWN_HINT = "鼠标悬停托盘图标时显示倒计时"
SETTINGS_CLOSE_ACTION = "关闭窗口时"
SETTINGS_CLOSE_ASK = "每次询问"
SETTINGS_CLOSE_TRAY = "总是最小化到托盘"
SETTINGS_CLOSE_EXIT = "总是退出程序"
SETTINGS_SAVE = "保存"
SETTINGS_CANCEL = "取消"
MSG_SETTINGS_SAVED = "设置已保存"
ERR_SETTINGS_SAVE_FAILED = "保存设置失败：{message}"

# --- 动作类型（v1.1 阶段 2）---
ACTION_SHUTDOWN = "关机"
ACTION_RESTART = "重启"
ACTION_LOCK = "锁定"
ACTION_HIBERNATE = "休眠"
SETTINGS_ACTION = "定时动作"
MODE_HINT = "当前模式：{mode}"
BTN_SET_TEMPLATE = "设定{mode}"
WARN_RESIDENT_TITLE = "计划依赖程序常驻"
WARN_RESIDENT_TEXT = (
    "当前的{mode}计划由本程序到点执行，退出后该计划将失效。\n\n确定退出吗？"
)
DLG_SWITCH_ACTION_TITLE = "切换定时动作"
DLG_SWITCH_ACTION_TEXT = "切换动作类型将取消当前计划（{when} {mode}）。\n\n确定切换吗？"
