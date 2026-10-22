"""把一张方角/浅底的图标源图处理成多尺寸 .ico（圆角外透明）。

做法：
1. 自动定位圆角方块的真实边界（用深色图形中心 + 中心线扫描交叉校验）
2. 裁切成正方形
3. 从左上角对角线自动估算圆角半径
4. 逐尺寸缩放后套圆角裁剪，圆角外完全透明
5. 手写 ICO 容器（内嵌 PNG，Vista 以后支持，不需要 Pillow）

用法：
    python scripts/make_icon.py <源图> [输出.ico]
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)
WHITE_FLOOR = 250  # 三通道都 >= 此值视为背景白


def _is_background(color: QColor) -> bool:
    return min(color.red(), color.green(), color.blue()) >= WHITE_FLOOR


def find_tile(img: QImage) -> tuple[int, int, int]:
    """返回 (左, 上, 边长)：圆角方块的紧凑正方形边界。"""
    width, height = img.width(), img.height()

    # 用深色主体（外圈、指针）定位中心，避免受四角噪点影响
    min_x, min_y, max_x, max_y = width, height, 0, 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            color = img.pixelColor(x, y)
            if max(color.red(), color.green(), color.blue()) < 100:
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)

    if max_x <= min_x:
        raise SystemExit("没有找到深色主体，无法定位图标边界")

    cx, cy = (min_x + max_x) // 2, (min_y + max_y) // 2

    def scan_line(fixed: int, horizontal: bool, forward: bool) -> int | None:
        span = width if horizontal else height
        indices = range(span) if forward else range(span - 1, -1, -1)
        for index in indices:
            color = img.pixelColor(index, fixed) if horizontal else img.pixelColor(fixed, index)
            if not _is_background(color):
                return index
        return None

    left, right = scan_line(cy, True, True), scan_line(cy, True, False)
    top, bottom = scan_line(cx, False, True), scan_line(cx, False, False)
    if None in (left, right, top, bottom):
        raise SystemExit("边界扫描失败")

    # 深色主体通常占方块约 0.83，用它交叉校验，避免被边缘噪点带偏
    dark_diameter = max(max_x - min_x, max_y - min_y)
    estimated = round(dark_diameter / 0.832)
    measured_w = right - left + 1
    measured_h = bottom - top + 1

    # 取三者最小值：任何一边被 JPEG 噪点撑大都只会让图标留下白边
    side = min(estimated, measured_w, measured_h, width, height)
    left = max(0, cx - side // 2)
    top = max(0, cy - side // 2)
    side = min(side, width - left, height - top)
    return left, top, side


def detect_corner_radius(img: QImage, max_probe: int = 200) -> float:
    """沿左上对角线找第一个实体像素，反推圆角半径。"""
    probe = min(max_probe, img.width() // 2)
    for step in range(probe):
        if not _is_background(img.pixelColor(step, step)):
            # 圆角圆弧与对角线交点距角点 = r * (1 - 1/√2)
            return max(step / 0.29289, 8.0)
    return img.width() * 0.145


def render_rounded(source: QImage, size: int, radius_ratio: float) -> QImage:
    scaled = source.scaled(
        size,
        size,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QImage(size, size, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    radius = max(1.0, size * radius_ratio)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)
    painter.drawImage(0, 0, scaled)
    painter.end()
    return canvas


def to_png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def build_ico(png_by_size: dict[int, bytes], sizes: tuple[int, ...]) -> bytes:
    count = len(sizes)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries, payload = b"", b""

    for size in sizes:
        data = png_by_size[size]
        # 256 在字段里写 0
        dimension = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset
        )
        offset += len(data)
        payload += data

    return header + entries + payload


def build_preview(images: dict[int, QImage], out_path: Path) -> None:
    """拼一张对比图：左边 256 原尺寸，右边各尺寸实际像素，底部 16px 放大 4 倍。"""
    pad, gap = 24, 30

    width = 760
    height = 380

    preview = QImage(width, height, QImage.Format.Format_ARGB32)
    preview.fill(QColor("#FFFFFF"))

    painter = QPainter(preview)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

    # 左：256 原尺寸
    painter.drawImage(pad, pad, images[256])
    painter.setPen(QColor("#7A828F"))
    painter.drawText(pad, pad + 256 + 18, "256")

    # 右：64 / 48 / 32 实际尺寸，纵向排列对比
    x = pad + 256 + gap
    y = pad
    for size in (64, 48, 32, 16):
        painter.drawImage(x, y, images[size])
        painter.drawText(x + size + 10, y + size // 2 + 4, f"{size}px")
        y += size + 10

    # 下：16px 放大 4 倍看清晰度
    y2 = pad + 256 + 28
    painter.drawText(pad, y2 + 10, "16px 放大 4 倍：")
    scaled = images[16].scaled(
        64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
    )
    painter.drawImage(pad + 120, y2, scaled)

    painter.end()
    preview.save(str(out_path))


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("用法: python scripts/make_icon.py <源图> [输出.ico]")
        return 2

    source_path = Path(args[0])
    output_path = Path(args[1]) if len(args) > 1 else (
        Path(__file__).resolve().parent.parent / "assets" / "app.ico"
    )

    app = QGuiApplication(sys.argv[:1])  # noqa: F841

    source = QImage(str(source_path))
    if source.isNull():
        print(f"读不到图片：{source_path}")
        return 1
    source = source.convertToFormat(QImage.Format.Format_ARGB32)
    print(f"源图: {source.width()}x{source.height()}")

    left, top, side = find_tile(source)
    tile = source.copy(left, top, side, side)
    print(f"方块: 从 ({left},{top}) 起，边长 {side}")

    radius = detect_corner_radius(tile)
    ratio = radius / side
    print(f"圆角半径: {radius:.0f}px（占 {ratio:.1%}）")

    rendered = {size: render_rounded(tile, size, ratio) for size in SIZES}
    png_by_size = {size: to_png_bytes(image) for size, image in rendered.items()}

    ico_bytes = build_ico(png_by_size, SIZES)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ico_bytes)
    print(f"已生成: {output_path}  ({len(ico_bytes)} 字节, {len(SIZES)} 个尺寸)")

    preview_path = output_path.parent.parent / "logs" / "icon_preview.png"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    build_preview(rendered, preview_path)
    print(f"预览图: {preview_path}")

    # 单独存一张 256 的 png，方便直接看透明效果
    png_path = output_path.with_suffix(".png")
    rendered[256].save(str(png_path))
    print(f"PNG:    {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
