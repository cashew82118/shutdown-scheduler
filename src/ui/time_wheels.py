"""时 / 分数字轮盘。

规格见 docs/03-设计规范.md §5.2：200×132，行高 44，可见 3 行。

交互：
- 滚轮 / 上下键：作用于光标所在（或激活的）列，每次 ±1
- 鼠标拖拽：累计位移每满一行步进一次
- 左右键：切换激活列
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    Qt,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ui import styles

ROW_HEIGHT = 44.0
WHEEL_WIDTH = 200
WHEEL_HEIGHT = 132
ANIM_MS = 160
COLUMN_GAP = 24.0

COL_HOUR = 0
COL_MINUTE = 1


class TimeWheels(QWidget):
    """两列滚轮。"""

    timeChanged = pyqtSignal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(WHEEL_WIDTH, WHEEL_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.SizeVerCursor)

        self._hour = 20
        self._minute = 0
        self._active = COL_HOUR

        # 每列独立的滚动偏移与动画：只让被操作的那一列动
        self._accent = styles.ACCENT
        self._offsets = [0.0, 0.0]
        self._anims: list[QVariantAnimation] = []
        for column in range(2):
            anim = QVariantAnimation(self)
            anim.setDuration(ANIM_MS)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.valueChanged.connect(
                lambda value, col=column: self._on_anim_tick(value, col)
            )
            self._anims.append(anim)

        self._drag_y = 0.0
        self._dragging = False

    # -- 对外接口 ---------------------------------------------------------

    def time(self) -> tuple[int, int]:
        return self._hour, self._minute

    def set_accent(self, color: str) -> None:
        """主题色联动：激活列指示线随动作模式变色。"""
        if color != self._accent:
            self._accent = color
            self.update()

    def set_time(self, hour: int, minute: int, animate: bool = False) -> None:
        """外部设置（表盘联动时调用），不回发信号。"""
        hour %= 24
        minute %= 60
        if (hour, minute) == (self._hour, self._minute):
            return

        old_hour, old_minute = self._hour, self._minute
        direction = 1 if (hour * 60 + minute) > (old_hour * 60 + old_minute) else -1
        self._hour, self._minute = hour, minute
        if animate:
            if hour != old_hour:
                self._roll(COL_HOUR, direction)
            if minute != old_minute:
                self._roll(COL_MINUTE, direction)
        self.update()

    # -- 数值变更 ---------------------------------------------------------

    def _step(self, column: int, delta: int) -> None:
        if column == COL_HOUR:
            self._hour = (self._hour + delta) % 24
        else:
            self._minute = (self._minute + delta) % 60

        self._roll(column, delta)
        self.update()
        self.timeChanged.emit(self._hour, self._minute)

    def _roll(self, column: int, delta: int) -> None:
        """滚动动画：新值从它原本所在的方向滑入。

        值 +1（选到下面更大的数）→ 内容先下移 44px 再归位，视觉上新值从下方升起；
        值 -1 → 内容先上移，新值从上方落下。
        """
        anim = self._anims[column]
        anim.stop()
        anim.setStartValue(float(delta * ROW_HEIGHT))
        anim.setEndValue(0.0)
        anim.start()

    def _on_anim_tick(self, value: object, column: int) -> None:
        self._offsets[column] = float(value)
        self.update()

    # -- 事件 -------------------------------------------------------------

    def _column_at(self, x: float) -> int:
        return COL_HOUR if x < self.width() / 2 else COL_MINUTE

    def wheelEvent(self, event) -> None:
        column = self._column_at(event.position().x())
        # 方向约定：向下滚 = 选下面那个更大的数（与拖拽一致）
        steps = -event.angleDelta().y() / 120.0
        # 每格滚轮 ±1，快速滚动时一次可能跨多格
        delta = int(round(steps))
        if delta:
            self._step(column, delta)
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._active = self._column_at(event.position().x())
            self._dragging = True
            self._drag_y = event.position().y()
            self.setFocus()
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            return
        y = event.position().y()
        diff = y - self._drag_y
        while abs(diff) >= ROW_HEIGHT:
            direction = 1 if diff > 0 else -1
            # 方向约定：向下拖 = 选下面那个更大的数
            self._step(self._active, direction)
            self._drag_y += direction * ROW_HEIGHT
            diff = y - self._drag_y

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            for anim in self._anims:
                anim.stop()
            self._offsets = [0.0, 0.0]
            self.update()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Up:
            self._step(self._active, 1)
        elif key == Qt.Key.Key_Down:
            self._step(self._active, -1)
        elif key == Qt.Key.Key_Left:
            self._active = COL_HOUR
            self.update()
        elif key == Qt.Key.Key_Right:
            self._active = COL_MINUTE
            self.update()
        else:
            super().keyPressEvent(event)

    # -- 绘制 -------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center_y = self.height() / 2.0

        # 中间高亮行
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(styles.BG))
        painter.drawRoundedRect(
            QRectF(4, center_y - ROW_HEIGHT / 2, self.width() - 8, ROW_HEIGHT), 8.0, 8.0
        )

        left_cx = (self.width() - COLUMN_GAP) / 4.0
        right_cx = self.width() - left_cx

        self._draw_column(painter, self._hour, 24, left_cx, center_y, COL_HOUR)
        self._draw_column(painter, self._minute, 60, right_cx, center_y, COL_MINUTE)
        self._draw_colon(painter, self.width() / 2.0, center_y)

    def _draw_column(
        self,
        painter: QPainter,
        value: int,
        modulo: int,
        center_x: float,
        center_y: float,
        column: int,
    ) -> None:
        for delta in (-1, 0, 1):
            shown = (value + delta) % modulo
            top = (
                center_y
                + delta * ROW_HEIGHT
                - ROW_HEIGHT / 2
                + self._offsets[column]
            )
            rect = QRectF(center_x - 44, top, 88, ROW_HEIGHT)

            selected = delta == 0
            color = QColor(styles.TEXT if selected else styles.TEXT_DISABLED)
            if not selected:
                color.setAlpha(150)

            font = QFont()
            font.setFamilies(["Microsoft YaHei UI", "Segoe UI"])
            font.setPixelSize(22)
            font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QPen(color))
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignCenter),
                f"{shown:02d}",
            )

        # 激活列指示：底部一条细线
        if column == self._active and self.hasFocus():
            pen = QPen(QColor(self._accent))
            pen.setWidthF(2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            y = self.height() - 8
            painter.drawLine(
                QPointF(center_x - 14, y),
                QPointF(center_x + 14, y),
            )

    def _draw_colon(self, painter: QPainter, cx: float, cy: float) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(styles.TEXT_DISABLED))
        painter.drawEllipse(QPointF(cx, cy - 7), 2.2, 2.2)
        painter.drawEllipse(QPointF(cx, cy + 7), 2.2, 2.2)
