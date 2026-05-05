import fitz
import json
from pathlib import Path

# ── Settings ─────────────────────────────────────────────────────────────────
CASE_JSON    = "dataset/case_001.json"
TEMPLATE_PDF = "templates/fog_blank.pdf"
OUTPUT_PDF   = "rendered_forms/case_001_fog.pdf"
PAGE_INDEX   = 4

CASE_ID   = "CASE-001"
CASE_DATE = "26.03.2026"

# ── Column x-positions (moved further right of circles) ──────────────────────
# Each column cell is ~33px wide. Circles sit at left of cell.
# X should sit clearly to the RIGHT of the circle.
COL = {
    "a": 385,   # ON  / OFF
    "b": 418,   # ON  / ON
    "c": 451,   # OFF / OFF
    "d": 484,   # OFF / ON
}

# ── Row y-positions ───────────────────────────────────────────────────────────
# Fixed: removed incorrect entries in gap rows (between sections)
ROW_Y = {
    "1":  233,
    "2":  252,
    "3":  271,
    "4":  290,
    # gap row between section 1 and 2 — no data
    "5":  320,
    "6":  339,
    "7":  358,
    "8":  377,
    # gap row between section 2 and 3 — no data
    "9":  407,
    "10": 426,
    "11": 445,
    "12": 464,
}

# Gesamtscore row — placed AFTER the circle in each column
TOTAL_Y = 485
# ─────────────────────────────────────────────────────────────────────────────


def place(page, x, y, text, size=8, color=(0, 0, 0)):
    page.insert_text((x, y), str(text), fontsize=size, color=color)


def cover(page, x0, y0, x1, y1):
    """Draw white rectangle to erase existing content."""
    page.draw_rect(fitz.Rect(x0, y0, x1, y1),
                   color=(1, 1, 1), fill=(1, 1, 1))


def get_nested_answers(response_item: dict) -> dict:
    result = {}
    for child in response_item.get("item", []):
        link_id = child["linkId"]
        answers = child.get("answer", [])
        if answers and "valueBoolean" in answers[0]:
            result[link_id] = answers[0]["valueBoolean"]
    return result


def main():
    with open(CASE_JSON, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    doc  = fitz.open(TEMPLATE_PDF)
    page = doc[PAGE_INDEX]

    # ── Cover existing header values ──────────────────────────────────────────
    cover(page, 355, 44, 540, 65)   # ID field area
    cover(page, 355, 63, 540, 84)   # Datum field area

    # ── Write new header ──────────────────────────────────────────────────────
    place(page, 420, 57,  CASE_ID,   size=10)
    place(page, 420, 75,  CASE_DATE, size=10)

    # ── Score rows ────────────────────────────────────────────────────────────
    col_order = [
        ("a", COL["a"]),
        ("b", COL["b"]),
        ("c", COL["c"]),
        ("d", COL["d"]),
    ]

    totals = {"a": 0, "b": 0, "c": 0, "d": 0}

    for group_item in case_data.get("item", []):
        row_id  = group_item["linkId"]
        answers = get_nested_answers(group_item)

        if row_id not in ROW_Y:
            continue

        y = ROW_Y[row_id]

        for suffix, col_x in col_order:
            link_id = f"{row_id}{suffix}"
            value   = answers.get(link_id, False)
            if value:
                place(page, col_x, y, "X", size=9)
                totals[suffix] += 1

    # ── Gesamtscore row ───────────────────────────────────────────────────────
    # Cover the existing circle symbols in the total row first
    cover(page, 358, 476, 510, 494)

    # Write totals clearly after circles
    place(page, COL["a"], TOTAL_Y, str(totals["a"]), size=9)
    place(page, COL["b"], TOTAL_Y, str(totals["b"]), size=9)
    place(page, COL["c"], TOTAL_Y, str(totals["c"]), size=9)
    place(page, COL["d"], TOTAL_Y, str(totals["d"]), size=9)

    # ── Save ─────────────────────────────────────────────────────────────────
    Path(OUTPUT_PDF).parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT_PDF)
    print(f" Saved → {OUTPUT_PDF}")
    print(f"   Totals → ON/OFF:{totals['a']}  ON/ON:{totals['b']}  "
          f"OFF/OFF:{totals['c']}  OFF/ON:{totals['d']}")


if __name__ == "__main__":
    main()