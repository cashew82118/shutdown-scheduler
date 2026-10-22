"""内置 SVG 图标与图标按钮。

图标一律手写 SVG 字符串，颜色用 {color} 占位符在绘制时注入，
这样同一个图标可以随 hover / 主题色变色，不需要多套资源文件。
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QPushButton

from ui import styles

GEAR = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
<g fill="none" stroke="{color}" stroke-width="1.9" stroke-linecap="round">
<circle cx="12" cy="12" r="6"/>
<line x1="12" y1="2.6" x2="12" y2="5"/>
<line x1="12" y1="19" x2="12" y2="21.4"/>
<line x1="2.6" y1="12" x2="5" y2="12"/>
<line x1="19" y1="12" x2="21.4" y2="12"/>
<line x1="5.4" y1="5.4" x2="7.2" y2="7.2"/>
<line x1="16.8" y1="7.2" x2="18.6" y2="5.4"/>
<line x1="5.4" y1="18.6" x2="7.2" y2="16.8"/>
<line x1="16.8" y1="16.8" x2="18.6" y2="18.6"/>
</g>
</svg>'''


def colored(svg: str, color: str) -> str:
    return svg.replace("{color}", color)


class IconButton(QPushButton):
    """手绘 SVG 图标按钮：hover 加深、带圆角底色，不用 emoji。"""

    def __init__(
        self,
        svg: str,
        size: tuple[int, int],
        tooltip: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._svg = svg
        self._hover = False
        self._pressed = False
        self.setFixedSize(*size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        if tooltip:
            self.setToolTip(tooltip)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # hover 底色（圆角小方块）
        if self._hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#E9ECF1"))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        if self._pressed:
            color = styles.TEXT_DISABLED
        elif self._hover:
            color = styles.TEXT
        else:
            color = styles.TEXT_SUB

        renderer = QSvgRenderer(QByteArray(colored(self._svg, color).encode("utf-8")))
        margin = 4
        renderer.render(
            painter,
            QRectF(
                margin,
                margin,
                self.width() - margin * 2,
                self.height() - margin * 2,
            ),
        )
        painter.end()
