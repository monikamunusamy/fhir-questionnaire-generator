use rand::Rng;
use serde::{Deserialize, Serialize};
use std::fs;
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
            // Highest priority: use explicit FHIR answerOption values
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

            // Rule-based generation when no answerOption exists
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

fn main() {
    let q_path = format!(
        "{}/questionnaires/fog_questionnaire.json",
        env!("CARGO_MANIFEST_DIR")
    );

    println!("Trying to load questionnaire from:\n{}", q_path);

    let data = fs::read_to_string(&q_path).expect("Failed to read questionnaire file");
    let q: Questionnaire = serde_json::from_str(&data).expect("Invalid questionnaire JSON");

    if let Some(title) = &q.title {
        println!("Loaded questionnaire: {}", title);
    }

    let dataset_dir = format!("{}/dataset", env!("CARGO_MANIFEST_DIR"));

    if !Path::new(&dataset_dir).exists() {
        fs::create_dir(&dataset_dir).expect("Failed to create dataset directory");
    }

    let num_cases = 20;

    for i in 1..=num_cases {
        let qr = generate_questionnaire_response(&q);

        let json_file = format!("{}/case_{:03}.json", dataset_dir, i);

        let json_content =
            serde_json::to_string_pretty(&qr).expect("Failed to serialize response");

        fs::write(&json_file, json_content).expect("Failed to write dataset file");
    }

    println!("JSON cases generated successfully.");
}