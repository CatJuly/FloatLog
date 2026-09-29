"""生成 FloatLog 的应用图标（多尺寸 .ico + 预览 PNG）。

设计：蓝紫渐变的圆角方片（悬浮框）→ 底部柔和投影（悬浮感）→ 三条白色圆角日志行。
用法：python make_icon.py   # 产出 FloatLog.ico 与 icon_preview.png
"""

from PIL import Image, ImageDraw, ImageFilter

MASTER = 1024                      # 超采样母图，缩放时抗锯齿
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def draw_master() -> Image.Image:
    s = MASTER
    pad = int(s * 0.06)            # 方片距画布边缘
    lift = int(s * 0.035)          # 阴影下移量（悬浮感）
    corner = int(s * 0.22)         # 圆角半径
    x0, y0, x1, y1 = pad, pad, s - pad, s - pad

    # 1) 柔和投影（右下偏移 + 高斯模糊）
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [x0 + lift, y0 + lift, x1 + lift, y1 + lift],
        radius=corner, fill=(16, 42, 96, 150),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(s * 0.030))

    # 2) 渐变方片（蓝 400 → 蓝 700）
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    top, bottom = (96, 165, 250), (29, 78, 216)
    for y in range(y0, y1):
        c = _lerp(top, bottom, (y - y0) / (y1 - y0))
        td.line([(x0, y), (x1, y)], fill=c + (255,))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=corner, fill=255)
    tile.putalpha(mask)

    out = Image.alpha_composite(shadow, tile)

    # 3) 三条白色圆角日志行（左对齐，宽度错落）
    d = ImageDraw.Draw(out)
    lx = int(s * 0.21)
    line_h = int(s * 0.075)
    avail = s - 2 * lx
    for wfrac, yfrac in [(0.62, 0.30), (0.46, 0.46), (0.56, 0.62)]:
        y = int(yfrac * s)
        w = int(wfrac * avail)
        d.rounded_rectangle(
            [lx, y, lx + w, y + line_h], radius=line_h // 2,
            fill=(255, 255, 255, 245),
        )

    return out


def main() -> None:
    master = draw_master()
    master.save("icon_preview.png")
    master.resize((256, 256), Image.LANCZOS).save("FloatLog.ico",
                                                  format="ICO", sizes=SIZES)
    print("wrote FloatLog.ico (multi-size) + icon_preview.png")


if __name__ == "__main__":
    main()
