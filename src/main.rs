use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
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
    #[serde(default)]
    item: Vec<QuestionItem>,
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
    #[serde(skip_serializing_if = "Vec::is_empty")]
    #[serde(default)]
    item: Vec<ResponseItem>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    #[serde(default)]
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

fn generate_boolean(link_id: &str, rng: &mut StdRng) -> Answer {
    // Last character of linkId is the condition suffix: a, b, c, d
    let condition = link_id.chars().last().unwrap_or('b');

    // Realistic freezing probabilities per condition:
    // a = Stim ON  / Med OFF  — some benefit from stimulation
    // b = Stim ON  / Med ON   — best condition, lowest freezing
    // c = Stim OFF / Med OFF  — worst condition, highest freezing
    // d = Stim OFF / Med ON   — medication helps but no stim
    let prob = match condition {
        'a' => 0.30,
        'b' => 0.18,
        'c' => 0.58,
        'd' => 0.38,
        _   => 0.35,
    };

    Answer {
        value_string:  None,
        value_integer: None,
        value_boolean: Some(rng.gen_bool(prob)),
    }
}

fn generate_response_item(q: &QuestionItem, rng: &mut StdRng) -> ResponseItem {
    if q.qtype == "group" {
        let nested: Vec<ResponseItem> = q
            .item
            .iter()
            .map(|child| generate_response_item(child, rng))
            .collect();
        ResponseItem {
            link_id: q.link_id.clone(),
            item:    nested,
            answer:  vec![],
        }
    } else {
        let answer = generate_boolean(&q.link_id, rng);
        ResponseItem {
            link_id: q.link_id.clone(),
            item:    vec![],
            answer:  vec![answer],
        }
    }
}

fn generate_questionnaire_response(
    q: &Questionnaire,
    case_number: u64,
) -> QuestionnaireResponse {
    // Seed per case — reproducible but different for each case
    let mut rng = StdRng::seed_from_u64(case_number * 137);

    let items: Vec<ResponseItem> = q
        .item
        .iter()
        .map(|it| generate_response_item(it, &mut rng))
        .collect();

    QuestionnaireResponse {
        resource_type: "QuestionnaireResponse".to_string(),
        questionnaire: q.id.clone(),
        status:        "completed".to_string(),
        item:          items,
    }
}

fn main() {
    let q_path = format!(
        "{}/questionnaires/fog_questionnaire.json",
        env!("CARGO_MANIFEST_DIR")
    );

    println!("Loading: {}", q_path);
    let data = fs::read_to_string(&q_path).expect("Failed to read questionnaire");
    let q: Questionnaire = serde_json::from_str(&data).expect("Invalid JSON");

    if let Some(title) = &q.title {
        println!("Questionnaire: {}", title);
    }

    let dataset_dir = format!("{}/dataset", env!("CARGO_MANIFEST_DIR"));
    if !Path::new(&dataset_dir).exists() {
        fs::create_dir(&dataset_dir).expect("Failed to create dataset dir");
    }

    let num_cases = 100;
    for i in 1..=num_cases {
        let qr = generate_questionnaire_response(&q, i as u64);
        let json_file = format!("{}/case_{:03}.json", dataset_dir, i);
        let json_content = serde_json::to_string_pretty(&qr).expect("Serialize failed");
        fs::write(&json_file, json_content).expect("Write failed");
    }

    println!("  Generated {} JSON cases in dataset/", num_cases);
}
