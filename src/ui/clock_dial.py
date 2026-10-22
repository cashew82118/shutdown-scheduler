"""自绘圆形表盘（真实双针）。

规格见 docs/03-设计规范.md §5.1。

时间语义（关键设计）
------------------
表盘只有 12 小时刻度，而目标是 24 小时时刻，消歧规则：

- **拖时针**：只改小时，分钟保持不变；指针绕过 12 点时翻转上午/下午。
- **拖分针**：只改分钟，每绕一圈小时 ±1（和拨真表一样）。
- **点空白处**：快速定位，两根针一起跳到该时刻，小时取「离当前最近」的那个。
"""

from __future__ import annotations

import math

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    Qt,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

from ui import styles

DIAL_MARGIN = 8
SNAP_MINUTES = 5
ANIM_MS = 150
GRAB_TOLERANCE = 18.0
"""按下位置与某根针的角度差在此范围内，视为抓住该针。"""

MODE_QUICK = "quick"
MODE_HOUR = "hour"
MODE_MINUTE = "minute"


def _shortest(target: float, current: float) -> float:
    """从 current 转到 target 的最短角差（-180..180）。"""
    return (target - current + 180.0) % 360.0 - 180.0


class ClockDial(QWidget):
    """圆形表盘。拖时针改小时，拖分针改分钟，点空白处快速定位。"""

    timeChanged = pyqtSignal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(styles.DIAL_SIZE, styles.DIAL_SIZE)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._hour = 20
        self._minute = 0

        # 两根针的绘制角度（0 = 12 点方向，顺时针）
        self._hour_hand = self._hour_angle()
        self._minute_hand = self._minute_angle()

        self._dragging = False
        self._drag_mode = ""
        self._drag_angle = 0.0
        self._keyboard_focus = False
        self._accent = styles.ACCENT

        # 时针模式
        self._drag_hour_base = 0.0
        self._drag_pm = False

        # 分针模式
        self._drag_minute_base = 0.0
        self._drag_start_hour = 0

        # 快速定位模式
        self._drag_total_base = 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_anim_tick)
        self._h_from = self._h_delta = 0.0
        self._m_from = self._m_delta = 0.0

    # -- 对外接口 ---------------------------------------------------------

    def time(self) -> tuple[int, int]:
        return self._hour, self._minute

    def set_accent(self, color: str) -> None:
        """主题色联动（FR-14）：中心点与焦点环随动作模式变色。"""
        if color != self._accent:
            self._accent = color
            self.update()

    def set_time(self, hour: int, minute: int, animate: bool = True) -> None:
        """外部设置时间（轮盘联动时调用），不回发信号。"""
        self._hour = hour % 24
        self._minute = minute % 60
        hour_angle = self._hour_angle()
        minute_angle = self._minute_angle()

        if animate and not self._dragging:
            self._animate_to(hour_angle, minute_angle)
        else:
            self._anim.stop()
            self._hour_hand = hour_angle
            self._minute_hand = minute_angle
            self.update()

    # -- 角度换算 ---------------------------------------------------------

    def _hour_angle(self) -> float:
        return ((self._hour % 12) * 30.0 + self._minute * 0.5) % 360.0

    def _minute_angle(self) -> float:
        return (self._minute * 6.0) % 360.0

    def _geometry(self) -> tuple[float, float, float]:
        rect = self.rect().adjusted(DIAL_MARGIN, DIAL_MARGIN, -DIAL_MARGIN, -DIAL_MARGIN)
        return float(rect.center().x()), float(rect.center().y()), rect.width() / 2.0

    def _angle_from_pos(self, x: float, y: float) -> float:
        cx, cy, _ = self._geometry()
        return math.degrees(math.atan2(x - cx, cy - y)) % 360.0

    def _pick_hour(self, hour12: int) -> int:
        """在 hour12 与 hour12+12 中选与当前小时更接近的（环形距离）。"""

        def ring_distance(a: int, b: int) -> int:
            diff = abs(a - b) % 24
            return min(diff, 24 - diff)

        return min((hour12, hour12 + 12), key=lambda h: ring_distance(h, self._hour))

    # -- 动画 -------------------------------------------------------------

    def _animate_to(self, hour_angle: float, minute_angle: float) -> None:
        self._anim.stop()
        self._h_from = self._hour_hand
        self._h_delta = _shortest(hour_angle, self._hour_hand)
        self._m_from = self._minute_hand
        self._m_delta = _shortest(minute_angle, self._minute_hand)
        self._anim.start()

    def _on_anim_tick(self, value: object) -> None:
        progress = float(value)
        self._hour_hand = (self._h_from + self._h_delta * progress) % 360.0
        self._minute_hand = (self._m_from + self._m_delta * progress) % 360.0
        self.update()

    # -- 拖动 -------------------------------------------------------------

    def _inside(self, x: float, y: float) -> bool:
        cx, cy, r = self._geometry()
        distance = math.hypot(x - cx, y - cy)
        return 20.0 <= distance <= r

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if self._inside(pos.x(), pos.y()):
                self._anim.stop()
                self._dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.setFocus()
                self._begin_drag(pos.x(), pos.y())

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            pos = event.position()
            self._drag_to(pos.x(), pos.y())

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._drag_to(event.position().x(), event.position().y())
            mode = self._drag_mode
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._snap(mode)
            self._drag_mode = ""

    def _begin_drag(self, x: float, y: float) -> None:
        angle = self._angle_from_pos(x, y)
        self._drag_angle = angle

        to_minute = abs(_shortest(angle, self._minute_angle()))
        to_hour = abs(_shortest(angle, self._hour_angle()))

        if to_minute <= GRAB_TOLERANCE and to_minute <= to_hour:
            self._drag_mode = MODE_MINUTE
            self._drag_minute_base = float(self._minute)
            self._drag_start_hour = self._hour
        elif to_hour <= GRAB_TOLERANCE:
            self._drag_mode = MODE_HOUR
            self._drag_hour_base = self._hour_angle() / 30.0
            self._drag_pm = self._hour >= 12
        else:
            self._drag_mode = MODE_QUICK
            total = angle / 360.0 * 720.0
            hour12 = int(total // 60) % 12
            minute = min(int(round(total % 60)), 59)
            hour = self._pick_hour(hour12)
            self._drag_pm = hour >= 12
            self._drag_total_base = (hour % 12) * 60 + minute
            self._apply(hour, minute)

    def _drag_to(self, x: float, y: float) -> None:
        angle = self._angle_from_pos(x, y)
        delta = _shortest(angle, self._drag_angle)
        self._drag_angle = angle

        if self._drag_mode == MODE_MINUTE:
            self._drag_minute_base += delta / 360.0 * 60.0
            laps = int(self._drag_minute_base // 60)
            minute = min(int(self._drag_minute_base % 60), 59)
            hour = (self._drag_start_hour + laps) % 24
            self._minute_hand = angle
            self._hour_hand = ((hour % 12) * 30.0 + minute * 0.5) % 360.0
            self._apply(hour, minute)

        elif self._drag_mode == MODE_HOUR:
            self._drag_hour_base += delta / 360.0 * 12.0
            laps = int(self._drag_hour_base // 12)
            # 指针角度里含有「分钟造成的偏移」，先扣掉再取整，才是用户想指的小时
            hour12 = int(math.floor(self._drag_hour_base % 12 - self._minute / 60.0 + 0.5)) % 12
            is_pm = self._drag_pm ^ (laps % 2 == 1)
            hour = hour12 + 12 if is_pm else hour12
            self._hour_hand = angle
            self._apply(hour, self._minute)

        elif self._drag_mode == MODE_QUICK:
            self._drag_total_base += delta / 360.0 * 720.0
            laps = int(self._drag_total_base // 720)
            pos = self._drag_total_base % 720
            hour12 = int(pos // 60) % 12
            minute = min(int(pos % 60), 59)
            is_pm = self._drag_pm ^ (laps % 2 == 1)
            hour = hour12 + 12 if is_pm else hour12
            self._apply(hour, minute)

    def _snap(self, mode: str) -> None:
        """松手：分钟吸附到 5 分钟，指针重新对齐真实角度。

        拖时针时分钟本来就没动，不能顺手吸附，否则会莫名其妙改掉用户原来的分钟数。
        """
        hour, minute = self._hour, self._minute
        if mode in (MODE_QUICK, MODE_MINUTE):
            minute = int(math.floor(minute / SNAP_MINUTES + 0.5)) * SNAP_MINUTES
            if minute >= 60:
                minute -= 60
                hour = (hour + 1) % 24

        self._hour, self._minute = hour, minute
        self._hour_hand = self._hour_angle()
        self._minute_hand = self._minute_angle()
        self.update()
        self.timeChanged.emit(hour, minute)

    def _apply(self, hour: int, minute: int) -> None:
        changed = (hour, minute) != (self._hour, self._minute)
        self._hour, self._minute = hour, minute
        self.update()
        if changed:
            self.timeChanged.emit(hour, minute)

    def keyPressEvent(self, event) -> None:
        step_hour = 0
        step_minute = 0
        key = event.key()
        if key == Qt.Key.Key_Left:
            step_hour = -1
        elif key == Qt.Key.Key_Right:
            step_hour = 1
        elif key == Qt.Key.Key_Up:
            step_minute = 1
        elif key == Qt.Key.Key_Down:
            step_minute = -1
        else:
            super().keyPressEvent(event)
            return

        total = (self._hour * 60 + self._minute + step_hour * 60 + step_minute) % 1440
        hour, minute = divmod(total, 60)
        self._hour, self._minute = hour, minute
        self._animate_to(self._hour_angle(), self._minute_angle())
        self.timeChanged.emit(hour, minute)

    # -- 绘制 -------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cx, cy, r = self._geometry()
        self._draw_face(painter, cx, cy, r)
        self._draw_ticks(painter, cx, cy, r)
        self._draw_numbers(painter, cx, cy, r)

        # 分针在下（长而细），时针在上（短而粗），层次与真表一致
        self._draw_hand(painter, cx, cy, self._minute_hand, r * 0.70, 3.0, styles.HAND)
        self._draw_hand(painter, cx, cy, self._hour_hand, r * 0.48, 5.5, styles.HAND)
        self._draw_center(painter, cx, cy)

    def _draw_face(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        gradient = QRadialGradient(cx, cy, r)
        gradient.setColorAt(0.0, QColor(styles.DIAL_BG_INNER))
        gradient.setColorAt(1.0, QColor(styles.DIAL_BG))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        pen = QPen(QColor("#2E3546"))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r - 0.5, r - 0.5)

    def _draw_ticks(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        outer = r - 12.0

        for index in range(60):
            major = index % 5 == 0
            angle = math.radians(index * 6.0)
            length = 8.0 if major else 4.0
            pen = QPen(QColor(styles.TICK_MAJOR if major else styles.TICK_MINOR))
            pen.setWidthF(2.0 if major else 1.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            sin_a, cos_a = math.sin(angle), math.cos(angle)
            painter.drawLine(
                QPointF(cx + sin_a * (outer - length), cy - cos_a * (outer - length)),
                QPointF(cx + sin_a * outer, cy - cos_a * outer),
            )

    def _draw_numbers(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        font = QFont()
        font.setFamilies(["Microsoft YaHei UI", "Segoe UI"])
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QPen(QColor(styles.DIAL_NUM)))

        radius = r * 0.74
        for hour in range(1, 13):
            angle = math.radians(hour * 30.0)
            x = cx + math.sin(angle) * radius
            y = cy - math.cos(angle) * radius
            painter.drawText(
                QRectF(x - 14, y - 11, 28, 22),
                int(Qt.AlignmentFlag.AlignCenter),
                str(hour),
            )

    def _draw_hand(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        angle: float,
        length: float,
        width: float,
        color: str,
    ) -> None:
        rad = math.radians(angle)
        sin_a, cos_a = math.sin(rad), math.cos(rad)

        pen = QPen(QColor(color))
        pen.setWidthF(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        tail = width * 2.6
        painter.drawLine(
            QPointF(cx - sin_a * tail, cy + cos_a * tail),
            QPointF(cx + sin_a * length, cy - cos_a * length),
        )

    def _draw_center(self, painter: QPainter, cx: float, cy: float) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._accent))
        painter.drawEllipse(QPointF(cx, cy), 6.5, 6.5)

        if self._keyboard_focus:
            pen = QPen(QColor(self._accent))
            pen.setWidthF(1.6)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), 13.0, 13.0)

    # -- 焦点 -------------------------------------------------------------

    def focusInEvent(self, event) -> None:
        # 只有 Tab 切进来才画焦点环：鼠标点击、窗口激活都不该在表盘中心多出一个圈
        self._keyboard_focus = event.reason() in (
            Qt.FocusReason.TabFocusReason,
            Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason,
        )
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._keyboard_focus = False
        self.update()
        super().focusOutEvent(event)
