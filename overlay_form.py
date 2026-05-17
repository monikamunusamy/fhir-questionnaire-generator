import fitz
import json
import random
import math
from pathlib import Path

TEMPLATE_PDF = "templates/fog_blank.pdf"
PAGE_INDEX   = 4

COL_X = {"a": 378, "b": 411, "c": 447, "d": 482}
ROW_Y = {
    "1": 214, "2": 232, "3": 251, "4": 270,
    "5": 310, "6": 328, "7": 347, "8": 366,
    "9": 405, "10": 424, "11": 444, "12": 463,
}
TOTAL_Y = 481
CELL_W, CELL_H = 33, 19
CIRCLE_R, X_SIZE = 6.5, 5.5
FONT_PATH = "handwriting.ttf"


def cover(page, x0, y0, x1, y1):
    page.draw_rect(fitz.Rect(x0,y0,x1,y1),
                   color=(1,1,1), fill=(1,1,1))


def jitter(val, amount=1.0):
    return val + random.uniform(-amount, amount)


def draw_realistic_circle(page, cx, cy):
    """Bezier circle with pressure simulation."""
    r     = CIRCLE_R * random.uniform(0.88, 1.05)
    cx    = jitter(cx, 1.2)
    cy    = jitter(cy, 1.0)
    gap   = random.uniform(5, 22)
    start = random.uniform(0, 360)
    steps = 32

    for i in range(steps):
        a1 = math.radians(start + (360-gap)*i/steps)
        a2 = math.radians(start + (360-gap)*(i+1)/steps)

        t        = i / steps
        pressure = 0.4 + 0.7 * math.sin(math.pi * t)
        width    = max(0.3, pressure * random.uniform(0.75, 1.1))

        p1 = fitz.Point(
            cx + (r+random.uniform(-0.4,0.4)) * math.cos(a1),
            cy + (r+random.uniform(-0.4,0.4)) * math.sin(a1)
        )
        p2 = fitz.Point(
            cx + (r+random.uniform(-0.4,0.4)) * math.cos(a2),
            cy + (r+random.uniform(-0.4,0.4)) * math.sin(a2)
        )
        page.draw_line(p1, p2, color=(0,0,0), width=width)


def draw_realistic_x(page, cx, cy):
    """Bezier X with pressure simulation."""
    s     = X_SIZE * random.uniform(0.88, 1.08)
    cx    = jitter(cx, 1.0)
    cy    = jitter(cy, 1.0)

    # Line 1 with pressure
    steps = 12
    for i in range(steps):
        t  = i / steps
        t2 = (i+1) / steps
        pressure = 0.5 + 0.6 * math.sin(math.pi * t)
        width    = max(0.4, pressure * random.uniform(0.9, 1.3))

        x1 = cx - s + 2*s*t  + jitter(0, 0.4)
        y1 = cy - s + 2*s*t  + jitter(0, 0.4)
        x2 = cx - s + 2*s*t2 + jitter(0, 0.4)
        y2 = cy - s + 2*s*t2 + jitter(0, 0.4)

        page.draw_line(fitz.Point(x1,y1), fitz.Point(x2,y2),
                       color=(0,0,0), width=width)

    # Line 2 with pressure
    for i in range(steps):
        t  = i / steps
        t2 = (i+1) / steps
        pressure = 0.5 + 0.6 * math.sin(math.pi * t)
        width    = max(0.4, pressure * random.uniform(0.9, 1.3))

        x1 = cx + s - 2*s*t  + jitter(0, 0.4)
        y1 = cy - s + 2*s*t  + jitter(0, 0.4)
        x2 = cx + s - 2*s*t2 + jitter(0, 0.4)
        y2 = cy - s + 2*s*t2 + jitter(0, 0.4)

        page.draw_line(fitz.Point(x1,y1), fitz.Point(x2,y2),
                       color=(0,0,0), width=width)


def add_scan_noise(page, seed):
    random.seed(seed + 999)
    pw = page.rect.width
    ph = page.rect.height

    # Dust specks
    for _ in range(random.randint(10, 30)):
        page.draw_circle(
            fitz.Point(random.uniform(10,pw-10),
                       random.uniform(10,ph-10)),
            random.uniform(0.3, 1.0),
            color=(0,0,0), fill=(0,0,0)
        )

    # Scan lines
    for _ in range(random.randint(3, 8)):
        gray = random.uniform(0.80, 0.93)
        page.draw_line(
            fitz.Point(0, random.uniform(30, ph-30)),
            fitz.Point(pw, random.uniform(30, ph-30)),
            color=(gray,gray,gray),
            width=random.uniform(0.3, 1.0)
        )

    # Edge shadow
    gray = random.uniform(0.83, 0.93)
    w    = random.uniform(4, 9)
    page.draw_rect(fitz.Rect(0,0,w,ph),
                   color=(gray,gray,gray), fill=(gray,gray,gray))
    page.draw_rect(fitz.Rect(pw-w,0,pw,ph),
                   color=(gray,gray,gray), fill=(gray,gray,gray))


def place(page, x, y, text, size=9, color=(0,0,0)):
    page.insert_text((x,y), str(text), fontsize=size, color=color)


def get_nested_answers(item):
    result = {}
    for child in item.get("item", []):
        lid = child["linkId"]
        ans = child.get("answer", [])
        if ans and "valueBoolean" in ans[0]:
            result[lid] = ans[0]["valueBoolean"]
    return result


def render_fog_case(case_json_path, output_pdf_path,
                    case_id, case_date, seed):
    random.seed(seed)

    with open(case_json_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    doc  = fitz.open(TEMPLATE_PDF)
    page = doc[PAGE_INDEX]

    col_order = [("a",COL_X["a"]),("b",COL_X["b"]),
                 ("c",COL_X["c"]),("d",COL_X["d"])]

    # Header
    cover(page, 355, 42, 560, 90)
    place(page, jitter(420,1), jitter(57,1), case_id,   size=10)
    place(page, jitter(420,1), jitter(76,1), case_date, size=10)

    # Erase score cells
    for y in list(ROW_Y.values()) + [TOTAL_Y]:
        cover(page,
              COL_X["a"]-CELL_W//2, y-CELL_H//2,
              COL_X["d"]+CELL_W//2, y+CELL_H//2)

    # Answers
    answers_map = {}
    for gi in case_data.get("item", []):
        answers_map[gi["linkId"]] = get_nested_answers(gi)

    totals = {"a":0,"b":0,"c":0,"d":0}

    for row_id, yc in ROW_Y.items():
        answers = answers_map.get(row_id, {})
        for suffix, cx in col_order:
            value = answers.get(f"{row_id}{suffix}", False)
            if value:
                draw_realistic_x(page, cx, yc)
                totals[suffix] += 1
            else:
                draw_realistic_circle(page, cx, yc)

    # Gesamtscore
    cover(page,
          COL_X["a"]-CELL_W//2, TOTAL_Y-CELL_H//2,
          COL_X["d"]+CELL_W//2, TOTAL_Y+CELL_H//2)
    for suffix, cx in col_order:
        draw_realistic_circle(page, cx, TOTAL_Y)
        num = str(totals[suffix])
        place(page, cx-3, TOTAL_Y+3, num, size=7)

    # Scan noise
    add_scan_noise(page, seed)

    # Save only FOG page
    out = fitz.open()
    out.insert_pdf(doc, from_page=PAGE_INDEX, to_page=PAGE_INDEX)
    Path(output_pdf_path).parent.mkdir(parents=True, exist_ok=True)
    out.save(str(output_pdf_path))
    out.close()
    doc.close()

    return totals


def main():
    dataset_dir  = Path("dataset")
    rendered_dir = Path("rendered_forms")
    rendered_dir.mkdir(exist_ok=True)

    case_files = sorted(dataset_dir.glob("case_*.json"))
    if not case_files:
        print("❌  Run 'cargo run' first.")
        return

    print(f"📋  Generating {len(case_files)} cases...\n")

    for case_file in case_files:
        stem    = case_file.stem
        num_str = stem.replace("case_", "")
        output  = rendered_dir / f"fog_{stem}.pdf"

        totals = render_fog_case(
            case_json_path  = str(case_file),
            output_pdf_path = output,
            case_id         = f"CASE-{num_str}",
            case_date       = "26.03.2026",
            seed            = int(num_str) * 137,
        )
        print(f"  ✅  CASE-{num_str}  "
              f"a:{totals['a']} b:{totals['b']} "
              f"c:{totals['c']} d:{totals['d']}")

    print(f"\n🎉  Done — {len(case_files)} PDFs in rendered_forms/")


if __name__ == "__main__":
    main()