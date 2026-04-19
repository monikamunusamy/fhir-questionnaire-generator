use printpdf::*;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::fs;
use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

#[derive(Debug, Deserialize)]
struct Questionnaire {
    #[serde(rename = "resourceType")]
    _resource_type: String,
    id: String,
    title: Option<String>,
    #[serde(rename = "status")]
    _status: String,
    item: Vec<QuestionItem>,
}

#[derive(Debug, Deserialize)]
struct QuestionItem {
    #[serde(rename = "linkId")]
    link_id: String,
    text: Option<String>,
    #[serde(rename = "type")]
    qtype: String,

    #[serde(default)]
    #[serde(rename = "answerOption")]
    answer_option: Vec<AnswerOption>,
}

#[derive(Debug, Deserialize)]
struct AnswerOption {
    #[serde(rename = "valueInteger")]
    value_integer: Option<i64>,

    #[serde(rename = "valueString")]
    _value_string: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct QuestionnaireResponse {
    #[serde(rename = "resourceType")]
    resource_type: String,
    questionnaire: String,
    status: String,
    item: Vec<ResponseItem>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ResponseItem {
    #[serde(rename = "linkId")]
    link_id: String,
    answer: Vec<Answer>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Answer {
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "valueString")]
    value_string: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "valueInteger")]
    value_integer: Option<i64>,

    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "valueBoolean")]
    value_boolean: Option<bool>,
}

fn generate_answer(qtype: &str, question_text: &str, options: &[AnswerOption]) -> Answer {
    let mut rng = rand::thread_rng();
    let text_lower = question_text.to_lowercase();

    match qtype {
        "string" => {
            if text_lower.contains("name") {
                let first_names = ["John", "Anna", "Max", "Sara", "Luca", "Mina"];
                let last_names = ["Miller", "Schmidt", "Khan", "Rossi", "Weber", "Ali"];

                let name = format!(
                    "{} {}",
                    first_names[rng.gen_range(0..first_names.len())],
                    last_names[rng.gen_range(0..last_names.len())]
                );

                Answer {
                    value_string: Some(name),
                    value_integer: None,
                    value_boolean: None,
                }
            } else {
                let generic_strings = [
                    "General entry",
                    "Synthetic text",
                    "Example value",
                    "Placeholder value",
                ];

                Answer {
                    value_string: Some(
                        generic_strings[rng.gen_range(0..generic_strings.len())].to_string(),
                    ),
                    value_integer: None,
                    value_boolean: None,
                }
            }
        }

        "text" => {
            let notes = if text_lower.contains("reason") {
                [
                    "Routine follow-up visit.",
                    "Mild tremor reported.",
                    "Medication adjustment requested.",
                    "Patient reports worsening symptoms.",
                ]
            } else if text_lower.contains("note") || text_lower.contains("comment") {
                [
                    "No additional notes.",
                    "Symptoms stable since last visit.",
                    "Follow-up recommended.",
                    "Patient reports mild symptoms.",
                ]
            } else {
                [
                    "Generated text response.",
                    "Synthetic free-text entry.",
                    "No additional information.",
                    "Structured comment generated automatically.",
                ]
            };

            Answer {
                value_string: Some(notes[rng.gen_range(0..notes.len())].to_string()),
                value_integer: None,
                value_boolean: None,
            }
        }

        "integer" => {
            if !options.is_empty() {
                let valid_ints: Vec<i64> =
                    options.iter().filter_map(|o| o.value_integer).collect();

                if !valid_ints.is_empty() {
                    let picked = valid_ints[rng.gen_range(0..valid_ints.len())];
                    return Answer {
                        value_string: None,
                        value_integer: Some(picked),
                        value_boolean: None,
                    };
                }
            }

            let val = if text_lower.contains("age") {
                rng.gen_range(18..=90)
            } else if text_lower.contains("score")
                || text_lower.contains("severity")
                || text_lower.contains("tremor")
                || text_lower.contains("stability")
                || text_lower.contains("tapping")
                || text_lower.contains("turn")
                || text_lower.contains("passage")
                || text_lower.contains("start")
            {
                rng.gen_range(0..=3)
            } else {
                rng.gen_range(0..=100)
            };

            Answer {
                value_string: None,
                value_integer: Some(val),
                value_boolean: None,
            }
        }

        "boolean" => {
            let prob_true = if text_lower.contains("medication") {
                0.7
            } else if text_lower.contains("tremor") {
                0.6
            } else {
                0.5
            };

            Answer {
                value_string: None,
                value_integer: None,
                value_boolean: Some(rng.gen_bool(prob_true)),
            }
        }

        "date" => {
            let year = if text_lower.contains("birth") {
                rng.gen_range(1950..=2005)
            } else {
                rng.gen_range(2020..=2025)
            };

            let month = rng.gen_range(1..=12);
            let day = rng.gen_range(1..=28);

            Answer {
                value_string: Some(format!("{year:04}-{month:02}-{day:02}")),
                value_integer: None,
                value_boolean: None,
            }
        }

        _ => Answer {
            value_string: Some("unsupported-type".to_string()),
            value_integer: None,
            value_boolean: None,
        },
    }
}

fn generate_questionnaire_response(q: &Questionnaire) -> QuestionnaireResponse {
    let response_items: Vec<ResponseItem> = q
        .item
        .iter()
        .map(|it| {
            let q_text = it.text.as_deref().unwrap_or("");
            let ans = generate_answer(&it.qtype, q_text, &it.answer_option);

            ResponseItem {
                link_id: it.link_id.clone(),
                answer: vec![ans],
            }
        })
        .collect();

    QuestionnaireResponse {
        resource_type: "QuestionnaireResponse".to_string(),
        questionnaire: q.id.clone(),
        status: "completed".to_string(),
        item: response_items,
    }
}

fn answer_to_string(answer: &Answer) -> String {
    if let Some(v) = &answer.value_string {
        return v.clone();
    }
    if let Some(v) = answer.value_integer {
        return v.to_string();
    }
    if let Some(v) = answer.value_boolean {
        return if v { "Yes".to_string() } else { "No".to_string() };
    }
    "(empty)".to_string()
}

fn render_score_line(value: i64, options: &[AnswerOption]) -> String {
    let valid_ints: Vec<i64> = options.iter().filter_map(|o| o.value_integer).collect();

    if valid_ints.is_empty() {
        return value.to_string();
    }

    let parts: Vec<String> = valid_ints
        .iter()
        .map(|v| {
            if *v == value {
                format!("[X] {}", v)
            } else {
                format!("[ ] {}", v)
            }
        })
        .collect();

    parts.join("   ")
}

fn write_text_line(
    layer: &PdfLayerReference,
    font: &IndirectFontRef,
    text: &str,
    size: f32,
    x: f32,
    y: f32,
) {
    layer.use_text(text, size, Mm(x), Mm(y), font);
}

fn draw_line(layer: &PdfLayerReference, x1: f32, y1: f32, x2: f32, y2: f32) {
    let line = Line {
        points: vec![
            (Point::new(Mm(x1), Mm(y1)), false),
            (Point::new(Mm(x2), Mm(y2)), false),
        ],
        is_closed: false,
    };

    layer.add_line(line);
}

fn draw_cover_page(
    doc: &PdfDocumentReference,
    page: PdfPageIndex,
    layer_index: PdfLayerIndex,
    case_number: usize,
    total_score: i64,
) {
    let layer = doc.get_page(page).get_layer(layer_index);
    let font = doc
        .add_builtin_font(BuiltinFont::Helvetica)
        .expect("Failed to load font");

    write_text_line(&layer, &font, "Testing M. Parkinson", 20.0, 20.0, 270.0);
    write_text_line(&layer, &font, "Synthetic Clinical Form", 12.0, 20.0, 260.0);

    draw_line(&layer, 20.0, 252.0, 190.0, 252.0);

    write_text_line(&layer, &font, "Case ID", 11.0, 20.0, 240.0);
    write_text_line(
        &layer,
        &font,
        &format!("CASE-{:03}", case_number),
        11.0,
        60.0,
        240.0,
    );

    write_text_line(&layer, &font, "Date", 11.0, 20.0, 230.0);
    write_text_line(&layer, &font, "2026-03-26", 11.0, 60.0, 230.0);

    write_text_line(&layer, &font, "Birth Date", 11.0, 20.0, 220.0);
    write_text_line(&layer, &font, "1965-04-27", 11.0, 60.0, 220.0);

    write_text_line(&layer, &font, "Clinical Overview", 14.0, 20.0, 200.0);
draw_line(&layer, 20.0, 196.0, 190.0, 196.0);

    write_text_line(&layer, &font, "Assessment Type: FOG", 11.0, 20.0, 182.0);
    write_text_line(&layer, &font, "Visit Type: Follow-up", 11.0, 20.0, 172.0);
    write_text_line(
    &layer,
    &font,
    &format!("FOG Total Score: {}", total_score),
    11.0,
    20.0,
    162.0,
);

    write_text_line(&layer, &font, "Signatures / Notes", 12.0, 20.0, 110.0);
    draw_line(&layer, 20.0, 100.0, 140.0, 100.0);
    draw_line(&layer, 20.0, 85.0, 140.0, 85.0);
    draw_line(&layer, 20.0, 70.0, 140.0, 70.0);
}

fn draw_fog_page(
    doc: &PdfDocumentReference,
    page: PdfPageIndex,
    layer_index: PdfLayerIndex,
    questionnaire: &Questionnaire,
    response: &QuestionnaireResponse,
    case_number: usize,
) {
    let layer = doc.get_page(page).get_layer(layer_index);
    let font = doc
        .add_builtin_font(BuiltinFont::Helvetica)
        .expect("Failed to load font");

    write_text_line(&layer, &font, "Freezing of Gait Score (FOG)", 18.0, 10.0, 280.0);
    write_text_line(&layer, &font, "ID", 11.0, 150.0, 286.0);
    write_text_line(
        &layer,
        &font,
        &format!("CASE-{:03}", case_number),
        11.0,
        165.0,
        286.0,
    );
    write_text_line(&layer, &font, "Date", 11.0, 150.0, 278.0);
    write_text_line(&layer, &font, "2026-03-26", 11.0, 165.0, 278.0);

    let start_y: f32 = 255.0;
    let row_height: f32 = 12.0;
    let rows = questionnaire.item.len() as i32 + 2;

    for i in 0..=rows {
        let y = start_y - i as f32 * row_height;
        draw_line(&layer, 10.0, y, 200.0, y);
    }

    draw_line(&layer, 10.0, start_y, 10.0, start_y - rows as f32 * row_height);
    draw_line(&layer, 30.0, start_y, 30.0, start_y - rows as f32 * row_height);
    draw_line(&layer, 120.0, start_y, 120.0, start_y - rows as f32 * row_height);
    draw_line(&layer, 200.0, start_y, 200.0, start_y - rows as f32 * row_height);

    write_text_line(&layer, &font, "Item", 10.0, 14.0, start_y - 8.0);
    write_text_line(&layer, &font, "Task", 10.0, 40.0, start_y - 8.0);
    write_text_line(&layer, &font, "Score", 10.0, 130.0, start_y - 8.0);

    for (i, q_item) in questionnaire.item.iter().enumerate() {
        let y = start_y - (i as f32 + 2.0) * row_height + 4.0;

        write_text_line(&layer, &font, &(i + 1).to_string(), 10.0, 14.0, y);

        let task_text = q_item.text.clone().unwrap_or_default();
        write_text_line(&layer, &font, &task_text, 9.0, 34.0, y);

        let response_item = response.item.iter().find(|r| r.link_id == q_item.link_id);

        if let Some(item) = response_item {
            let value = item.answer[0].value_integer.unwrap_or(0);
            let score_line = render_score_line(value, &q_item.answer_option);
            write_text_line(&layer, &font, &score_line, 9.0, 124.0, y);
        }
    }

    let total: i64 = response
        .item
        .iter()
        .map(|r| r.answer[0].value_integer.unwrap_or(0))
        .sum();

    let total_y = start_y - (questionnaire.item.len() as f32 + 2.0) * row_height + 4.0;
    write_text_line(&layer, &font, "Total Score", 10.0, 34.0, total_y);
    write_text_line(
        &layer,
        &font,
        &format!("{}", total),
        10.0,
        170.0,
        total_y,
    );

    let legend_top = 180.0;
    write_text_line(&layer, &font, "Legend", 12.0, 10.0, legend_top);

    draw_line(&layer, 10.0, 172.0, 200.0, 172.0);
    draw_line(&layer, 10.0, 160.0, 200.0, 160.0);
    draw_line(&layer, 10.0, 148.0, 200.0, 148.0);
    draw_line(&layer, 10.0, 136.0, 200.0, 136.0);

    draw_line(&layer, 10.0, 172.0, 10.0, 136.0);
    draw_line(&layer, 40.0, 172.0, 40.0, 136.0);
    draw_line(&layer, 80.0, 172.0, 80.0, 136.0);
    draw_line(&layer, 120.0, 172.0, 120.0, 136.0);
    draw_line(&layer, 160.0, 172.0, 160.0, 136.0);
    draw_line(&layer, 200.0, 172.0, 200.0, 136.0);

    write_text_line(&layer, &font, "Score", 9.0, 15.0, 164.0);
    write_text_line(&layer, &font, "0", 9.0, 52.0, 164.0);
    write_text_line(&layer, &font, "1", 9.0, 92.0, 164.0);
    write_text_line(&layer, &font, "2", 9.0, 132.0, 164.0);
    write_text_line(&layer, &font, "3", 9.0, 172.0, 164.0);

    write_text_line(&layer, &font, "Meaning", 9.0, 15.0, 152.0);
    write_text_line(&layer, &font, "None", 8.0, 45.0, 152.0);
    write_text_line(&layer, &font, "Mild", 8.0, 85.0, 152.0);
    write_text_line(&layer, &font, "Moderate", 8.0, 125.0, 152.0);
    write_text_line(&layer, &font, "Severe", 8.0, 165.0, 152.0);
}

fn render_case_pdf(
    questionnaire: &Questionnaire,
    response: &QuestionnaireResponse,
    file_path: &str,
    case_number: usize,
) {
    let (doc, cover_page, cover_layer) =
        PdfDocument::new("Parkinson Case", Mm(210.0), Mm(297.0), "Cover");

    let total: i64 = response
        .item
        .iter()
        .map(|r| r.answer[0].value_integer.unwrap_or(0))
        .sum();

    draw_cover_page(&doc, cover_page, cover_layer, case_number, total);

    let (fog_page, fog_layer) = doc.add_page(Mm(210.0), Mm(297.0), "FOG");
    draw_fog_page(&doc, fog_page, fog_layer, questionnaire, response, case_number);

    let mut writer =
        BufWriter::new(File::create(file_path).expect("Failed to create case PDF file"));
    doc.save(&mut writer).expect("Failed to save case PDF");
}

fn main() {
    let q_path = format!(
        "{}/questionnaires/fog_questionnaire.json",
        env!("CARGO_MANIFEST_DIR")
    );

    println!("Trying to load questionnaire from:\n{}", q_path);

    let data = fs::read_to_string(&q_path).expect("Failed to read questionnaire file");
    let q: Questionnaire = serde_json::from_str(&data).expect("Invalid questionnaire JSON");

    let dataset_dir = format!("{}/dataset", env!("CARGO_MANIFEST_DIR"));
    let rendered_dir = format!("{}/rendered_forms", env!("CARGO_MANIFEST_DIR"));

    if !Path::new(&dataset_dir).exists() {
        fs::create_dir(&dataset_dir).expect("Failed to create dataset directory");
    }

    if !Path::new(&rendered_dir).exists() {
        fs::create_dir(&rendered_dir).expect("Failed to create rendered_forms directory");
    }

    let num_cases = 20;

    for i in 1..=num_cases {
        let qr = generate_questionnaire_response(&q);

        let json_file = format!("{}/case_{:03}.json", dataset_dir, i);
        let pdf_file = format!("{}/case_{:03}.pdf", rendered_dir, i);

        let json_content =
            serde_json::to_string_pretty(&qr).expect("Failed to serialize response");
        fs::write(&json_file, json_content).expect("Failed to write dataset file");

        render_case_pdf(&q, &qr, &pdf_file, i);
    }

    println!("PDF cases generated successfully.");
}