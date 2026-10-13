# -*- coding: utf-8 -*-
"""
生成小程序 tabBar 图标（81x81 PNG，RGBA）

为什么用脚本生成而不是引入图片素材：
- 图标是纯几何线性图形，脚本生成体积最小（几百字节），且颜色能严格锁死品牌色
- 不依赖 Pillow，只用标准库 zlib/struct，任何环境都能跑

品牌色（PRD 11.1）：
  未选中 #9AA0A4（中性灰）  选中 #5B7FA5（法蓝）
如需调整图标形状，改 draw_* 函数里的几何判定即可。
"""

import os
import struct
import zlib

SIZE = 81
GREY = (154, 160, 164, 255)
BLUE = (91, 127, 165, 255)
EMPTY = (0, 0, 0, 0)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "miniprogram", "assets", "icons")


def _png(path, pixels):
    """pixels: 二维列表，每项为 (r,g,b,a)"""
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0
        for px in row:
            raw += bytes(px)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8bit RGBA
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)


def blank():
    return [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]


def _stroke(px, x, y, color, w=3):
    """以 (x,y) 为中心画一个 w×w 的方块（线性图标用描边近似）"""
    for dy in range(-(w // 2), w // 2 + 1):
        for dx in range(-(w // 2), w // 2 + 1):
            yy, xx = y + dy, x + dx
            if 0 <= yy < SIZE and 0 <= xx < SIZE:
                px[yy][xx] = color


def _line(px, x0, y0, x1, y1, color, w=3):
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(steps + 1):
        t = i / steps
        _stroke(px, int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), color, w)


def _rect(px, x0, y0, x1, y1, color, w=3):
    _line(px, x0, y0, x1, y0, color, w)
    _line(px, x1, y0, x1, y1, color, w)
    _line(px, x1, y1, x0, y1, color, w)
    _line(px, x0, y1, x0, y0, color, w)


def draw_home(color):
    """房子：屋顶三角 + 墙体矩形"""
    px = blank()
    # 屋顶
    _line(px, 14, 42, 40, 18, color)
    _line(px, 40, 18, 67, 42, color)
    # 墙体
    _rect(px, 22, 40, 59, 65, color)
    # 门
    _line(px, 40, 65, 40, 52, color)
    return px


def draw_learn(color):
    """打开的书：两页 + 中缝"""
    px = blank()
    _line(px, 12, 60, 40, 52, color)   # 左页下沿
    _line(px, 40, 52, 69, 60, color)   # 右页下沿
    _line(px, 12, 60, 12, 24, color)
    _line(px, 69, 60, 69, 24, color)
    _line(px, 12, 24, 40, 32, color)
    _line(px, 40, 32, 69, 24, color)
    _line(px, 40, 32, 40, 52, color)   # 中缝
    return px


def draw_profile(color):
    """人像：头 + 肩"""
    px = blank()
    # 头（圆形描边）
    import math
    cx, cy, r = 40, 27, 13
    for deg in range(0, 360, 3):
        a = math.radians(deg)
        _stroke(px, int(cx + r * math.cos(a)), int(cy + r * math.sin(a)), color, 3)
    # 肩（弧线）
    for deg in range(200, 340, 3):
        a = math.radians(deg)
        _stroke(px, int(40 + 24 * math.cos(a)), int(72 + 22 * math.sin(a)), color, 3)
    return px


def main():
    out = os.path.abspath(OUT_DIR)
    os.makedirs(out, exist_ok=True)
    jobs = [
        ("home.png", draw_home(GREY)),
        ("home-active.png", draw_home(BLUE)),
        ("learn.png", draw_learn(GREY)),
        ("learn-active.png", draw_learn(BLUE)),
        ("profile.png", draw_profile(GREY)),
        ("profile-active.png", draw_profile(BLUE)),
    ]
    for name, px in jobs:
        p = os.path.join(out, name)
        _png(p, px)
        print("生成 %s (%d bytes)" % (name, os.path.getsize(p)))


if __name__ == "__main__":
    main()
