use rand::Rng;
use serde::{Deserialize, Serialize};
use std::fs;

#[derive(Debug, Deserialize)]
struct Questionnaire {
    #[serde(rename = "resourceType")]
    resource_type: String,
    id: String,
    title: Option<String>,
    status: String,
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
    value_string: Option<String>,
}

#[derive(Debug, Serialize)]
struct QuestionnaireResponse {
    #[serde(rename = "resourceType")]
    resource_type: String,
    questionnaire: String,
    status: String,
    item: Vec<ResponseItem>,
}

#[derive(Debug, Serialize)]
struct ResponseItem {
    #[serde(rename = "linkId")]
    link_id: String,
    answer: Vec<Answer>,
}

#[derive(Debug, Serialize)]
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
        }

        "text" => {
            let notes = [
                "No additional notes.",
                "Patient reports mild symptoms.",
                "Follow-up recommended.",
                "Symptoms stable since last visit.",
            ];

            Answer {
                value_string: Some(notes[rng.gen_range(0..notes.len())].to_string()),
                value_integer: None,
                value_boolean: None,
            }
        }

        "integer" => {
            // 1) If FHIR answerOption exists, sample ONLY from allowed values (FHIR-constrained)
            if !options.is_empty() {
                let valid_ints: Vec<i64> = options.iter().filter_map(|o| o.value_integer).collect();
                if !valid_ints.is_empty() {
                    let picked = valid_ints[rng.gen_range(0..valid_ints.len())];
                    return Answer {
                        value_string: None,
                        value_integer: Some(picked),
                        value_boolean: None,
                    };
                }
            }

            // 2) Otherwise fall back to rule-based ranges
            let val = if text_lower.contains("age") {
                rng.gen_range(18..=90)
            } else if text_lower.contains("severity") || text_lower.contains("score") {
                rng.gen_range(0..=4)
            } else {
                rng.gen_range(0..=100)
            };

            Answer {
                value_string: None,
                value_integer: Some(val),
                value_boolean: None,
            }
        }

        "boolean" => Answer {
            value_string: None,
            value_integer: None,
            value_boolean: Some(rng.gen_bool(0.5)),
        },

        _ => Answer {
            value_string: Some("unsupported-type".to_string()),
            value_integer: None,
            value_boolean: None,
        },
    }
}

fn main() {
    // 1) Load Questionnaire
    let q_path = "questionnaires/basic_medical_questionnaire.json";
    let data = fs::read_to_string(q_path).expect("Failed to read questionnaire file");
    let q: Questionnaire = serde_json::from_str(&data).expect("Invalid questionnaire JSON");

    // 2) Generate QuestionnaireResponse items
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

    let qr = QuestionnaireResponse {
        resource_type: "QuestionnaireResponse".to_string(),
        questionnaire: q.id.clone(),
        status: "completed".to_string(),
        item: response_items,
    };

    // 3) Write to file
    let out_json = serde_json::to_string_pretty(&qr).expect("Failed to serialize response");
    fs::write("output_questionnaire_response.json", &out_json)
        .expect("Failed to write output file");

    println!(" Generated output_questionnaire_response.json");
}