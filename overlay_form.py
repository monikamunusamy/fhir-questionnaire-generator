"""
generate_assets.py
Creates handwritten X and O PNG stamp assets for the FOG overlay.

Run from the project folder:
    python3 generate_assets.py
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 180
SCALE = 3
CANVAS = SIZE * SCALE
CENTER = CANVAS // 2
X_COUNT = 64
O_COUNT = 64


def fresh_canvas():
    return Image.new("RGBA", (CANVAS, CANVAS), (255, 255, 255, 0))


def ink_color(rng):
    v = int(rng.integers(0, 34))
    a = int(rng.integers(236, 255))
    return (v, v, v, a)


def draw_segment(draw, p0, p1, width, color):
    draw.line([p0, p1], fill=color, width=max(1, int(width)), joint="curve")


def pressure_line(draw, pts, rng, base_width):
    n = len(pts) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        pressure = 0.48 + 0.82 * math.sin(math.pi * t)
        width = base_width * pressure * rng.uniform(0.85, 1.18)
        draw_segment(draw, pts[i], pts[i + 1], width, ink_color(rng))


def cubic_path(p0, p1, rng, steps=36, wobble=2.2):
    x0, y0 = p0
    x1, y1 = p1
    dx = x1 - x0
    dy = y1 - y0
    bend = rng.uniform(-0.11, 0.11)
    c1 = (x0 + dx * 0.30 - dy * bend + rng.uniform(-wobble, wobble),
          y0 + dy * 0.30 + dx * bend + rng.uniform(-wobble, wobble))
    c2 = (x0 + dx * 0.70 + dy * bend + rng.uniform(-wobble, wobble),
          y0 + dy * 0.70 - dx * bend + rng.uniform(-wobble, wobble))
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3 * x0 + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * x1
        y = mt**3 * y0 + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * y1
        pts.append((x + rng.normal(0, wobble * 0.22), y + rng.normal(0, wobble * 0.22)))
    return pts


def rotate_point(cx, cy, dx, dy, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)


def pen_stop(draw, x, y, rng, scale=1.0):
    if rng.random() > 0.58:
        return
    r = rng.uniform(1.0, 2.8) * SCALE * scale
    draw.ellipse([x - r, y - r, x + r, y + r], fill=ink_color(rng))


def crop_and_finish(img, rng):
    alpha = img.getchannel("A")
    if rng.random() < 0.55:
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.18, 0.42) * SCALE))
        img.putalpha(alpha)

    bbox = img.getbbox()
    if bbox is None:
        return img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

    pad = int(rng.uniform(18, 28) * SCALE)
    x0 = max(0, bbox[0] - pad)
    y0 = max(0, bbox[1] - pad)
    x1 = min(CANVAS, bbox[2] + pad)
    y1 = min(CANVAS, bbox[3] + pad)
    cropped = img.crop((x0, y0, x1, y1))

    out = Image.new("RGBA", (CANVAS, CANVAS), (255, 255, 255, 0))
    ox = (CANVAS - cropped.width) // 2 + int(rng.normal(0, 2.0 * SCALE))
    oy = (CANVAS - cropped.height) // 2 + int(rng.normal(0, 2.0 * SCALE))
    out.alpha_composite(cropped, (ox, oy))

    arr = np.array(out, dtype=np.float32)
    alpha_noise = rng.normal(0, 2.2, arr[:, :, 3].shape)
    arr[:, :, 3] = np.clip(arr[:, :, 3] + alpha_noise * (arr[:, :, 3] > 0), 0, 255)
    out = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return out.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def make_x(seed):
    rng = np.random.default_rng(seed)
    img = fresh_canvas()
    draw = ImageDraw.Draw(img)

    cx = CENTER + rng.uniform(-6, 6) * SCALE
    cy = CENTER + rng.uniform(-6, 6) * SCALE
    half = rng.uniform(30, 38) * SCALE
    overshoot = rng.uniform(1.5, 5.0) * SCALE
    angle = math.radians(rng.uniform(-9, 9))
    base_width = rng.uniform(3.8, 6.4) * SCALE

    h = half + overshoot
    first = (rotate_point(cx, cy, -h, -h, angle), rotate_point(cx, cy, h, h, angle))
    second = (rotate_point(cx, cy, h, -h, angle), rotate_point(cx, cy, -h, h, angle))

    for start, end in (first, second):
        pts = cubic_path(start, end, rng, steps=26, wobble=rng.uniform(0.45, 1.25) * SCALE)
        pressure_line(draw, pts, rng, base_width)
        pen_stop(draw, *start, rng, scale=0.75)
        pen_stop(draw, *end, rng, scale=0.75)

    if rng.random() < 0.18:
        pen_stop(draw, cx, cy, rng, scale=0.55)

    return crop_and_finish(img, rng)


def ellipse_points(cx, cy, rx, ry, angle, rng, steps=86, gap=None):
    start = rng.uniform(0, 360)
    gap_start = rng.uniform(0, 360) if gap else None
    pts = []
    for i in range(steps + 1):
        deg = (start + 360 * i / steps) % 360
        if gap is not None:
            gap_end = (gap_start + gap) % 360
            in_gap = deg > gap_start if gap_start < gap_end else deg > gap_start or deg < gap_end
            if in_gap:
                pts.append(None)
                continue
        theta = math.radians(deg)
        local_rx = rx + rng.normal(0, 1.2 * SCALE)
        local_ry = ry + rng.normal(0, 1.0 * SCALE)
        x = local_rx * math.cos(theta)
        y = local_ry * math.sin(theta)
        pts.append(rotate_point(cx, cy, x, y, angle))
    return pts


def pressure_polyline(draw, pts, rng, base_width):
    segment = []
    for pt in pts:
        if pt is None:
            if len(segment) > 1:
                pressure_line(draw, segment, rng, base_width)
            segment = []
        else:
            segment.append(pt)
    if len(segment) > 1:
        pressure_line(draw, segment, rng, base_width)


def make_o(seed):
    rng = np.random.default_rng(seed)
    img = fresh_canvas()
    draw = ImageDraw.Draw(img)

    cx = CENTER + rng.uniform(-6, 6) * SCALE
    cy = CENTER + rng.uniform(-6, 6) * SCALE
    rx = rng.uniform(23, 32) * SCALE
    ry = rng.uniform(26, 38) * SCALE
    angle = math.radians(rng.uniform(-12, 12))
    base_width = rng.uniform(4.0, 6.8) * SCALE
    gap = None

    pts = ellipse_points(cx, cy, rx, ry, angle, rng, gap=gap)
    pressure_polyline(draw, pts, rng, base_width)

    if rng.random() < 0.36:
        pen_stop(draw, *rotate_point(cx, cy, rx, 0, angle), rng, scale=0.55)
    return crop_and_finish(img, rng)


def make_preview(x_imgs, o_imgs, path):
    pad = 6
    cols = 8
    rows = ([x_imgs[i:i + cols] for i in range(0, len(x_imgs), cols)]
            + [[]]
            + [o_imgs[i:i + cols] for i in range(0, len(o_imgs), cols)])
    w = cols * (SIZE + pad) + pad
    h = len(rows) * (SIZE + pad) + pad
    grid = Image.new("RGB", (w, h), (218, 218, 218))
    for ri, row in enumerate(rows):
        for ci, img in enumerate(row):
            bg = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
            bg.paste(img, mask=img.getchannel("A"))
            grid.paste(bg, (pad + ci * (SIZE + pad), pad + ri * (SIZE + pad)))
    grid.save(path)


def main():
    x_dir = Path("assets/x_marks")
    o_dir = Path("assets/o_marks")
    x_dir.mkdir(parents=True, exist_ok=True)
    o_dir.mkdir(parents=True, exist_ok=True)

    x_imgs = []
    o_imgs = []
    print(f"Generating {X_COUNT} X marks...")
    for i in range(X_COUNT):
        img = make_x(i * 41 + 3)
        img.save(x_dir / f"x{i + 1:02d}.png")
        x_imgs.append(img)

    print(f"Generating {O_COUNT} O marks...")
    for i in range(O_COUNT):
        img = make_o(i * 43 + 7)
        img.save(o_dir / f"o{i + 1:02d}.png")
        o_imgs.append(img)

    make_preview(x_imgs, o_imgs, "assets/preview.png")
    print(f"Ready: {X_COUNT} X + {O_COUNT} O handwritten assets in assets/")


if __name__ == "__main__":
    main()
