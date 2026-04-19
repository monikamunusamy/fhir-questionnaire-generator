import fitz
import json

with open("dataset/case_001.json", "r", encoding="utf-8") as f:
    data = json.load(f)

doc = fitz.open("templates/fog_blank.pdf")
page = doc[0]

# --- adjust these coordinates by trial and error ---
case_id_pos = (420, 50)
date_pos = (420, 70)

# one test row only
score_cell_positions = {
    "1": {
        0: (470, 180),
        1: (490, 180),
        2: (510, 180),
        3: (530, 180),
    }
}

# header fields
page.insert_text(case_id_pos, "CASE-001")
page.insert_text(date_pos, "2026-03-26")

# first score row only
for item in data["item"]:
    link_id = item["linkId"]
    answer = item["answer"][0]

    if "valueInteger" in answer:
        value = answer["valueInteger"]

        if link_id in score_cell_positions and value in score_cell_positions[link_id]:
            x, y = score_cell_positions[link_id][value]
            page.insert_text((x, y), "X")

doc.save("rendered_forms/case_001_overlay.pdf")
print("Created rendered_forms/case_001_overlay.pdf")