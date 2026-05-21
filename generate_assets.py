"""
generate_assets.py
Generates realistic handwritten X and O mark PNG assets.
Run this once from your project folder:
    python3 generate_assets.py
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import math
import random
from pathlib import Path

SIZE    = 120
CENTER  = SIZE // 2
X_COUNT = 30
O_COUNT = 30


def fresh_canvas():
    return Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))


def pen_color(rng):
    v = int(rng.integers(8, 55))
    a = int(rng.integers(170, 250))
    return (v, v, v, a)


def pressure_widths(n, base, rng):
    widths = []
    for i in range(n):
        t = i / max(n - 1, 1)
        p = math.sin(math.pi * t) * rng.uniform(0.6, 1.4)
        w = max(1.0, base + p * rng.uniform(0.5, 1.2))
        widths.append(w)
    return widths


def wobble_path(x0, y0, x1, y1, rng, steps=20, wobble=1.8):
    pts = []
    mx = (x0 + x1) / 2 + rng.uniform(-3, 3)
    my = (y0 + y1) / 2 + rng.uniform(-3, 3)
    for i in range(steps + 1):
        t  = i / steps
        bx = (1-t)**2*x0 + 2*(1-t)*t*mx + t**2*x1
        by = (1-t)**2*y0 + 2*(1-t)*t*my + t**2*y1
        pts.append((bx + rng.uniform(-wobble, wobble),
                    by + rng.uniform(-wobble, wobble)))
    return pts


def draw_pressure_stroke(draw, pts, rng, base_w=2.5):
    widths = pressure_widths(len(pts) - 1, base_w, rng)
    for i in range(len(pts) - 1):
        c = pen_color(rng)
        w = max(1, int(widths[i]))
        draw.line([pts[i], pts[i+1]], fill=c, width=w)


def wobble_ellipse(cx, cy, rx, ry, rng,
                   steps=52, wobble=2.0, gap=None):
    start     = rng.uniform(0, 360)
    pts       = []
    gap_start = rng.uniform(0, 360) if gap else None
    for i in range(steps + 1):
        t     = i / steps
        angle = math.radians(start + 360 * t)
        deg   = (start + 360 * t) % 360
        if gap and gap_start is not None:
            ge     = (gap_start + gap) % 360
            in_gap = (deg > gap_start) if gap_start < ge \
                     else (deg > gap_start or deg < ge)
            if in_gap:
                pts.append(None)
                continue
        rnx = rx + rng.uniform(-wobble, wobble)
        rny = ry + rng.uniform(-wobble * 0.7, wobble * 0.7)
        pts.append((cx + rnx * math.cos(angle),
                    cy + rny * math.sin(angle)))
    return pts


def draw_ellipse_stroke(draw, pts, rng, base_w=2.2):
    seg = []
    for pt in pts:
        if pt is None:
            if len(seg) > 1:
                draw_pressure_stroke(draw, seg, rng, base_w)
            seg = []
        else:
            seg.append(pt)
    if len(seg) > 1:
        draw_pressure_stroke(draw, seg, rng, base_w)


def ink_bleed(img, rng):
    return img.filter(ImageFilter.GaussianBlur(
        radius=rng.uniform(0.5, 1.2)))


def paper_grain(img, rng):
    arr   = np.array(img).astype(np.float32)
    noise = rng.normal(0, 4, arr[:, :, 3].shape)
    arr[:, :, 3] = np.clip(arr[:, :, 3] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def add_stop(draw, x, y, rng):
    if rng.random() < 0.4:
        r = rng.uniform(0.8, 2.5)
        c = pen_color(rng)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=c)


def generate_x(seed):
    rng  = np.random.default_rng(seed)
    img  = fresh_canvas()
    draw = ImageDraw.Draw(img)
    size      = rng.uniform(22, 34)
    cx        = CENTER + rng.uniform(-5, 5)
    cy        = CENTER + rng.uniform(-5, 5)
    overshoot = rng.uniform(1.0, 5.0)
    base_w    = rng.uniform(1.8, 3.5)
    tilt      = math.radians(rng.uniform(-18, 18))
    cos_t     = math.cos(tilt)
    sin_t     = math.sin(tilt)
    def rot(dx, dy):
        return (cx + dx*cos_t - dy*sin_t, cy + dx*sin_t + dy*cos_t)
    h    = size / 2 + overshoot
    p1s  = rot(-h, -h); p1e = rot(h, h)
    pts1 = wobble_path(*p1s, *p1e, rng, steps=18, wobble=rng.uniform(1.0, 2.5))
    draw_pressure_stroke(draw, pts1, rng, base_w)
    add_stop(draw, *p1e, rng)
    p2s  = rot(h, -h); p2e = rot(-h, h)
    pts2 = wobble_path(*p2s, *p2e, rng, steps=18, wobble=rng.uniform(1.0, 2.5))
    draw_pressure_stroke(draw, pts2, rng, base_w)
    add_stop(draw, *p2e, rng)
    if rng.random() < 0.3:
        add_stop(draw, cx, cy, rng)
    return paper_grain(ink_bleed(img, rng), rng)


def generate_o(seed):
    rng  = np.random.default_rng(seed)
    img  = fresh_canvas()
    draw = ImageDraw.Draw(img)
    cx     = CENTER + rng.uniform(-4, 4)
    cy     = CENTER + rng.uniform(-4, 4)
    rx     = rng.uniform(16, 24)
    ry     = rng.uniform(14, 22)
    base_w = rng.uniform(1.6, 3.2)
    gap    = rng.uniform(6, 28) if rng.random() < 0.35 else None
    pts = wobble_ellipse(cx, cy, rx, ry, rng, steps=56,
                          wobble=rng.uniform(1.0, 2.8), gap=gap)
    draw_ellipse_stroke(draw, pts, rng, base_w)
    add_stop(draw, cx + rx, cy, rng)
    if rng.random() < 0.4:
        flat_y = cy + ry * 0.85
        draw.line([(cx - rx*0.4, flat_y), (cx + rx*0.4, flat_y)],
                  fill=pen_color(rng), width=max(1, int(base_w * 0.6)))
    return paper_grain(ink_bleed(img, rng), rng)


def save_preview(x_imgs, o_imgs, path):
    PAD = 6; COLS = 10; S = SIZE
    rows = ([x_imgs[i:i+COLS] for i in range(0, len(x_imgs), COLS)]
            + [[]]
            + [o_imgs[i:i+COLS] for i in range(0, len(o_imgs), COLS)])
    w = COLS*(S+PAD)+PAD; h = len(rows)*(S+PAD)+PAD
    grid = Image.new("RGB", (w, h), (220, 220, 220))
    for ri, row in enumerate(rows):
        for ci, img in enumerate(row):
            bg = Image.new("RGB", (S, S), (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            grid.paste(bg, (PAD+ci*(S+PAD), PAD+ri*(S+PAD)))
    grid.save(path)
    print(f"  Preview saved → {path}")


def main():
    x_dir = Path("assets/x_marks")
    o_dir = Path("assets/o_marks")
    x_dir.mkdir(parents=True, exist_ok=True)
    o_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating {X_COUNT} X marks...")
    x_imgs = []
    for i in range(X_COUNT):
        img = generate_x(seed=i*41+3)
        img.save(x_dir / f"x{i+1:02d}.png")
        x_imgs.append(img)
    print(f"Generating {O_COUNT} O marks...")
    o_imgs = []
    for i in range(O_COUNT):
        img = generate_o(seed=i*43+7)
        img.save(o_dir / f"o{i+1:02d}.png")
        o_imgs.append(img)
    save_preview(x_imgs, o_imgs, "assets/preview.png")
    print(f"\n✅  {X_COUNT} X + {O_COUNT} O assets ready in assets/")


if __name__ == "__main__":
    main()
