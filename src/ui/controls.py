"""自绘控件：滑动开关、分段选择器。

替代 QCheckBox / QRadioButton 的 QSS indicator 方案——后者在 Windows 上
渲染粗糙，且没有动画。

- ToggleSwitch：轨道 + 圆形滑块，140ms 缓动动画
- SegmentedControl：三态及以上互斥选择，选中项白底浮起
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
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ui import styles


class ToggleSwitch(QWidget):
    """滑动开关。点击切换，带 140ms 滑动动画。"""

    toggled = pyqtSignal(bool)

    TRACK_W = 44
    TRACK_H = 24
    THUMB_R = 10

    def __init__(self, checked: bool = False, on_color: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._on_color = on_color or styles.ACCENT
        self._position = 1.0 if checked else 0.0
        self.setFixedSize(self.TRACK_W, self.TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    @property
    def checked(self) -> bool:
        return self._checked

    def set_on_color(self, color: str) -> None:
        """主题色联动。"""
        if color != self._on_color:
            self._on_color = color
            self.update()

    def set_checked(self, checked: bool) -> None:
        if checked == self._checked:
            return
        self._checked = checked
        self._animate()
        self.toggled.emit(checked)

    def _animate(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._position)
        self._anim.setEndValue(1.0 if self._checked else 0.0)
        self._anim.start()

    def _on_anim(self, value: object) -> None:
        self._position = float(value)
        self.update()

    def _track_color(self) -> QColor:
        off = QColor("#C9CED7")
        on = QColor(self._on_color)
        t = self._position
        return QColor(
            round(off.red() + (on.red() - off.red()) * t),
            round(off.green() + (on.green() - off.green()) * t),
            round(off.blue() + (on.blue() - off.blue()) * t),
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._track_color())
        painter.drawRoundedRect(QRectF(0, 0, self.TRACK_W, self.TRACK_H), 12, 12)

        travel = self.TRACK_W - self.TRACK_H  # 20
        thumb_x = 2 + self._position * travel
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QPointF(thumb_x + self.TRACK_H / 2, self.TRACK_H / 2), self.THUMB_R, self.THUMB_R)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self._checked)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)


class CheckBox(QWidget):
    """自绘复选框：accent 填充 + 白色对勾，替代 QCheckBox 的原生 indicator。"""

    toggled = pyqtSignal(bool)

    BOX = 16

    def __init__(
        self, text: str = "", checked: bool = False, on_color: str | None = None, parent=None
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._checked = checked
        self._on_color = on_color or styles.ACCENT
        self._text_width = 0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_size()

    def _update_size(self) -> None:
        if self._text:
            font = QFont()
            font.setFamilies([styles.FONT_FAMILY])
            font.setPixelSize(13)
            metrics = QFontMetrics(font)
            self._text_width = metrics.horizontalAdvance(self._text)
        else:
            self._text_width = 0
        self.setFixedSize(self.BOX + (6 + self._text_width if self._text_width else 0), 20)

    @property
    def checked(self) -> bool:
        return self._checked

    def set_on_color(self, color: str) -> None:
        """主题色联动。"""
        if color != self._on_color:
            self._on_color = color
            self.update()

    def set_checked(self, checked: bool) -> None:
        if checked != self._checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(0, 2, self.BOX, self.BOX)
        if self._checked:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self._on_color))
            painter.drawRoundedRect(box, 4.5, 4.5)

            # 白色对勾
            pen = QPen(QColor("#FFFFFF"))
            pen.setWidthF(2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(QPointF(4.2, 10.2), QPointF(7.0, 13.0))
            painter.drawLine(QPointF(7.0, 13.0), QPointF(11.8, 7.0))
        else:
            pen = QPen(QColor(styles.BORDER))
            pen.setWidthF(1.5)
            painter.setPen(pen)
            painter.setBrush(QColor(styles.SURFACE))
            painter.drawRoundedRect(box, 4.5, 4.5)

        if self._text:
            font = QFont()
            font.setFamilies([styles.FONT_FAMILY])
            font.setPixelSize(13)
            painter.setFont(font)
            painter.setPen(QPen(QColor(styles.TEXT)))
            painter.drawText(QPointF(self.BOX + 6, 14), self._text)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self._checked)
        super().mousePressEvent(event)


class SegmentedControl(QWidget):
    """分段选择器：选项互斥，选中项白底浮起。"""

    selection_changed = pyqtSignal(int)

    HEIGHT = 32
    MIN_SEG_WIDTH = 84

    def __init__(self, options: list[str], current: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._options = list(options)
        self._current = current

        # 段宽按最长文字自适应，保证任何选项都不被截断
        font = QFont()
        font.setFamilies([styles.FONT_FAMILY])
        font.setPixelSize(12)
        metrics = QFontMetrics(font)
        longest = max((metrics.horizontalAdvance(o) for o in self._options), default=0)
        seg_width = max(self.MIN_SEG_WIDTH, longest + 28)
        self.setFixedSize(seg_width * len(self._options), self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def current(self) -> int:
        return self._current

    def set_current(self, index: int) -> None:
        if 0 <= index < len(self._options) and index != self._current:
            self._current = index
            self.update()
            self.selection_changed.emit(index)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 轨道底
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ECEEF2"))
        painter.drawRoundedRect(self.rect(), 8, 8)

        seg_w = self.width() / len(self._options)
        x = self._current * seg_w
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E3E6EB"), 1))
        painter.drawRoundedRect(QRectF(x + 2, 2, seg_w - 4, self.HEIGHT - 4), 7, 7)

        font = QFont()
        font.setFamilies([styles.FONT_FAMILY])
        font.setPixelSize(12)
        painter.setFont(font)

        for index, option in enumerate(self._options):
            selected = index == self._current
            painter.setPen(
                QPen(QColor(styles.TEXT if selected else styles.TEXT_SUB))
            )
            font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Normal)
            painter.setFont(font)
            rect = QRectF(index * seg_w, 0, seg_w, self.HEIGHT)
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), option)
        painter.end()

    def mousePressEvent(self, event) -> None:
        index = int(event.position().x() // (self.width() / len(self._options)))
        self.set_current(index)
        super().mousePressEvent(event)
