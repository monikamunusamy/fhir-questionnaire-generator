"""
overlay_form.py
Professional document degradation pipeline for synthetic FOG forms.

Stage 1: Load blank template PDF
Stage 2: Stamp handwritten PNG marks into cells
Stage 3: Flatten full page to raster image
Stage 4: Apply full document degradation:
         - paper tint + uneven illumination
         - scanner grain noise
         - ink bleed blur
         - JPEG compression artifacts
         - subtle page warp
         - scanner skew rotation
Stage 5: Save as final PDF — indistinguishable from real scanned form
"""

import fitz
import json, random, math, io
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance
from pathlib import Path

TEMPLATE_PDF = "templates/fog_blank.pdf"
PAGE_INDEX   = 4
ASSETS_DIR   = Path("assets")

# Score cell centres measured from the scanned template grid.
COL_X = {"a": 399, "b": 435, "c": 468, "d": 501}

ROW_Y = {
    "1":  214, "2":  232, "3":  251, "4":  270,
    "5":  310, "6":  328, "7":  347, "8":  366,
    "9":  405, "10": 424, "11": 444, "12": 463,
}
TOTAL_Y = 481
CELL_W  = 33
CELL_H  = 19
CELL_CLEAR_W = 31
CELL_CLEAR_H = 15


# ── Asset loader ──────────────────────────────────────────────────────────────
class MarkAssets:
    def __init__(self, d):
        self.xs = sorted((d/"x_marks").glob("*.png"))
        self.os = sorted((d/"o_marks").glob("*.png"))
        assert self.xs, "No X assets — run generate_assets.py first"
        assert self.os, "No O assets — run generate_assets.py first"
        print(f"  {len(self.xs)} X + {len(self.os)} O assets loaded")

    def rand_x(self): return Image.open(random.choice(self.xs)).copy()
    def rand_o(self): return Image.open(random.choice(self.os)).copy()


# ── Mark transform ────────────────────────────────────────────────────────────
def transform_mark(img, rng):
    """Apply rotation, scale, opacity — each mark unique."""
    # Rotation: clinicians tilt marks ±20 degrees
    angle = float(rng.uniform(-24, 24))
    img   = img.rotate(angle, expand=False,
                        resample=Image.BICUBIC,
                        fillcolor=(0, 0, 0, 0))
    # Scale: human marks vary, but should still fit inside the printed cell.
    sc  = float(rng.uniform(0.92, 1.18))
    nw  = max(10, int(img.width  * sc))
    nh  = max(10, int(img.height * sc))
    img = img.resize((nw, nh), Image.LANCZOS)
    # Opacity: pen pressure varies while staying legible after scan processing.
    alpha = img.split()[3]
    fac   = float(rng.uniform(0.88, 1.00))
    alpha = alpha.point(lambda p: int(p * fac))
    img.putalpha(alpha)
    return img


def stamp(page, pil_img, cx, cy, rng):
    """Stamp mark centred at cx,cy. Fills cell properly."""
    mark = transform_mark(pil_img, rng)

    # Human placement jitter — nobody marks exactly centre
    cx += float(rng.normal(0, 0.8))
    cy += float(rng.normal(0, 0.55))

    # Fill the score cell enough to look handwritten, not like a tiny icon.
    target_w = CELL_W * float(rng.uniform(0.84, 0.96))
    target_h = CELL_H * float(rng.uniform(1.00, 1.14))
    sc   = min(target_w / mark.width, target_h / mark.height)
    fw   = mark.width  * sc
    fh   = mark.height * sc
    rect = fitz.Rect(cx-fw/2, cy-fh/2, cx+fw/2, cy+fh/2)
    buf  = io.BytesIO()
    mark.save(buf, format="PNG")
    page.insert_image(rect, stream=buf.getvalue(), keep_proportion=True)


# ── Document degradation pipeline ─────────────────────────────────────────────
def degrade(pil_img, rng):
    """
    Full document degradation pipeline.
    Converts clean digital render into realistic scanned paper.
    """
    img = pil_img.convert("L")
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape

    # Scanner optics and paper are not perfectly even, but the reference remains
    # a high-contrast black-and-white clinical scan.
    img = Image.fromarray(arr.astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(0.18, 0.38))))
    img = ImageEnhance.Contrast(img).enhance(float(rng.uniform(1.15, 1.42)))
    img = ImageEnhance.Brightness(img).enhance(float(rng.uniform(1.00, 1.08)))
    arr = np.array(img, dtype=np.float32)

    yy, xx = np.mgrid[0:h, 0:w]
    lamp = (
        1.0
        + float(rng.uniform(-0.018, 0.020)) * ((xx - w / 2) / w)
        + float(rng.uniform(-0.018, 0.020)) * ((yy - h / 2) / h)
    )
    vignette = 1.0 - float(rng.uniform(0.018, 0.045)) * (
        ((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2
    )
    arr = arr * lamp * vignette

    paper_noise = rng.normal(0, float(rng.uniform(0.8, 1.8)), arr.shape)
    low_freq = rng.normal(0, 1, (max(2, h // 96), max(2, w // 96))).astype(np.float32)
    low_freq = cv2.resize(low_freq, (w, h), interpolation=cv2.INTER_CUBIC)
    arr = arr + paper_noise + low_freq * float(rng.uniform(1.0, 2.4))

    dark = arr < 150
    arr[dark] *= float(rng.uniform(0.80, 0.91))
    arr[~dark] = arr[~dark] * float(rng.uniform(0.97, 1.01)) + float(rng.uniform(1.0, 5.0))
    arr = np.clip(arr, 0, 255)

    # A tiny elastic warp gives scanned forms imperfect vertical/horizontal lines
    # without the slow per-pixel loop.
    amp_x = float(rng.uniform(0.25, 0.85))
    amp_y = float(rng.uniform(0.20, 0.65))
    map_x = (xx + amp_x * np.sin(2 * math.pi * yy / h + rng.uniform(0, math.pi))).astype(np.float32)
    map_y = (yy + amp_y * np.sin(2 * math.pi * xx / w + rng.uniform(0, math.pi))).astype(np.float32)
    arr = cv2.remap(arr.astype(np.uint8), map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    # Small dust/speckle, kept sparse so it reads as scanner noise rather than dirt.
    speckles = rng.random(arr.shape)
    arr[speckles < float(rng.uniform(0.00005, 0.00012))] = rng.integers(0, 45)
    arr[speckles > float(rng.uniform(0.99990, 0.99996))] = rng.integers(238, 256)

    img = Image.fromarray(arr.astype(np.uint8))
    if rng.random() < 0.75:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=int(rng.integers(90, 135)), threshold=3))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=int(rng.integers(78, 91)))
    buf.seek(0)
    img = Image.open(buf).convert("L")

    angle = float(rng.uniform(-0.45, 0.45))
    return img.rotate(angle, fillcolor=246, expand=False, resample=Image.BICUBIC)


# ── Helpers ───────────────────────────────────────────────────────────────────
def cover(page, x0, y0, x1, y1):
    page.draw_rect(fitz.Rect(x0, y0, x1, y1),
                   color=(1,1,1), fill=(1,1,1))

def clear_cell(page, cx, cy):
    page.draw_rect(
        fitz.Rect(
            cx - CELL_CLEAR_W / 2,
            cy - CELL_CLEAR_H / 2,
            cx + CELL_CLEAR_W / 2,
            cy + CELL_CLEAR_H / 2,
        ),
        color=(1, 1, 1),
        fill=(1, 1, 1),
    )

def redraw_score_grid(page):
    x_lines = [381, 418, 452, 485, 517]
    y_lines = [
        202.0, 221.2, 240.5, 259.7, 279.0,
        298.2, 317.2, 336.5, 355.8, 374.8,
        394.5, 413.7, 432.8, 452.2, 471.3, 491.2,
    ]
    for x in x_lines:
        page.draw_line((x, y_lines[0]), (x, y_lines[-1]), color=(0, 0, 0), width=0.75)
    for y in y_lines:
        page.draw_line((x_lines[0], y), (x_lines[-1], y), color=(0, 0, 0), width=0.75)

def place(page, x, y, text, size=9):
    page.insert_text((x, y), str(text), fontsize=size, color=(0,0,0))

def get_answers(item):
    r = {}
    for c in item.get("item", []):
        a = c.get("answer", [])
        if a and "valueBoolean" in a[0]:
            r[c["linkId"]] = a[0]["valueBoolean"]
    return r


def is_renderable_fog_case(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    if data.get("questionnaire") != "fog-score":
        return False

    for group in data.get("item", []):
        for child in group.get("item", []):
            answers = child.get("answer", [])
            if answers and "valueBoolean" in answers[0]:
                return True
    return False


# ── Main render ───────────────────────────────────────────────────────────────
def render_case(json_path, out_path, case_id, case_date, seed, assets):
    rng = np.random.default_rng(seed)
    random.seed(seed)

    with open(json_path, "r") as f:
        data = json.load(f)

    doc  = fitz.open(TEMPLATE_PDF)
    page = doc[PAGE_INDEX]

    cols = [("a",COL_X["a"]),("b",COL_X["b"]),
            ("c",COL_X["c"]),("d",COL_X["d"])]

    # Header
    cover(page, 355, 42, 560, 90)
    place(page, 420+float(rng.uniform(-1,1)),
                57 +float(rng.uniform(-1,1)), case_id,   size=10)
    place(page, 420+float(rng.uniform(-1,1)),
                76 +float(rng.uniform(-1,1)), case_date, size=10)

    ans_map = {gi["linkId"]: get_answers(gi)
               for gi in data.get("item", [])}
    totals  = {"a":0,"b":0,"c":0,"d":0}

    # Stamp marks
    for row_id, yc in ROW_Y.items():
        ans = ans_map.get(row_id, {})
        for suf, cx in cols:
            val  = ans.get(f"{row_id}{suf}", False)
            mark = assets.rand_x() if val else assets.rand_o()
            clear_cell(page, cx, yc)
            stamp(page, mark, cx, yc, rng)
            if val:
                totals[suf] += 1

    # Gesamtscore
    for suf, cx in cols:
        clear_cell(page, cx, TOTAL_Y)
        stamp(page, assets.rand_o(), cx, TOTAL_Y, rng)

    redraw_score_grid(page)

    # Render to high-res image (300 DPI)
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    pw  = page.rect.width
    ph  = page.rect.height
    doc.close()

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    # Apply full document degradation pipeline
    img = degrade(img, rng)

    # Save back as PDF at original page dimensions
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out_doc  = fitz.open()
    out_page = out_doc.new_page(width=pw, height=ph)
    out_page.insert_image(fitz.Rect(0,0,pw,ph), stream=buf.getvalue())
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(str(out_path))
    out_doc.close()

    return totals


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    print("📦  Loading assets...")
    assets = MarkAssets(ASSETS_DIR)

    ds = Path("dataset"); rd = Path("rendered_forms")
    rd.mkdir(exist_ok=True)

    cases = [p for p in sorted(ds.glob("case_*.json"))
             if is_renderable_fog_case(p)]
    if not cases:
        print("❌  No renderable fog-score case_*.json files found. Run 'cargo run' first.")
        return

    print(f"\n📋  Generating {len(cases)} cases...\n")

    for cf in cases:
        stem   = cf.stem
        num    = stem.replace("case_", "")
        out    = rd / f"fog_{stem}.pdf"
        totals = render_case(
            str(cf), out,
            f"CASE-{num}", "26.03.2026",
            int(num)*137, assets
        )
        print(f"    CASE-{num}  "
              f"a:{totals['a']} b:{totals['b']} "
              f"c:{totals['c']} d:{totals['d']}")

    print(f"\n🎉  {len(cases)} scanned PDFs in rendered_forms/")

if __name__ == "__main__":
    main()
