import fitz
import json
from pathlib import Path

CASE_ID = "CASE-001"
CASE_DATE = "26.03.2026"

CASE_JSON_PATH = "dataset/case_001.json"
TEMPLATE_CONFIG_PATH = "templates/fog_template.json"
OUTPUT_PDF_PATH = "rendered_forms/case_001_overlay.pdf"


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def insert_text(page, pos, text, fontsize=9):
    x, y = pos
    page.insert_text((x, y), str(text), fontsize=fontsize)


def main():
    case_data = load_json(CASE_JSON_PATH)
    template = load_json(TEMPLATE_CONFIG_PATH)

    pdf_path = template["pdf_path"]
    page_index = template["page_index"]
    header_fields = template["header_fields"]
    total_score_pos = template["total_score_pos"]
    score_cells = template["score_cells"]

    doc = fitz.open(pdf_path)
    page = doc[page_index]

    insert_text(page, header_fields["case_id"], CASE_ID, fontsize=9)
    insert_text(page, header_fields["date"], CASE_DATE, fontsize=9)

    total_score = 0

    for item in case_data["item"]:
        link_id = item["linkId"]
        answer = item["answer"][0]

        if "valueInteger" not in answer:
            continue

        value = answer["valueInteger"]
        total_score += value

        if link_id in score_cells:
            value_key = str(value)
            if value_key in score_cells[link_id]:
                insert_text(page, score_cells[link_id][value_key], "X", fontsize=10)

    insert_text(page, total_score_pos, total_score, fontsize=9)

    output_path = Path(OUTPUT_PDF_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"Created {OUTPUT_PDF_PATH}")


if __name__ == "__main__":
    main()