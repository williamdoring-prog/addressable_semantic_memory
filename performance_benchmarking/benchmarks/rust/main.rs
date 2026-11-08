use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::io::{self, Read, Write};
use std::process;
use std::time::Instant;

const METRIC_PREFIX: &str = "ASM-BENCH-METRICS ";

struct Fragment {
    address: String,
    text: String,
    score: usize,
    token_count: usize,
}

struct Lookup {
    address: String,
    text: Option<String>,
}

struct Input {
    id: String,
    question: String,
    budget: usize,
    lookups: Vec<String>,
    fragments: Vec<Fragment>,
}

struct Output {
    input_id: String,
    original_source_tokens: usize,
    question_tokens: usize,
    retrieved_addresses: Vec<String>,
    lookups: Vec<Lookup>,
    expanded: Vec<(String, String)>,
    context: String,
    context_tokens: usize,
    elapsed_ns: u128,
}

#[derive(Default)]
struct OperationMetrics {
    input_parse_ns: u128,
    retrieval_ns: u128,
    address_lookup_ns: u128,
    expansion_assembly_ns: u128,
    serialization_ns: u128,
}

fn unescape(value: &str) -> Result<String, String> {
    let mut output = String::with_capacity(value.len());
    let mut chars = value.chars();
    while let Some(ch) = chars.next() {
        if ch != '\\' {
            output.push(ch);
            continue;
        }
        match chars.next() {
            Some('\\') => output.push('\\'),
            Some('t') => output.push('\t'),
            Some('n') => output.push('\n'),
            Some('r') => output.push('\r'),
            Some(_) => return Err("invalid escape sequence".to_string()),
            None => return Err("invalid trailing escape".to_string()),
        }
    }
    Ok(output)
}

fn parse(input: &str) -> Result<Input, String> {
    let mut lines = input.lines();
    if lines.next().unwrap_or("").trim_end_matches('\r') != "ASM-BENCH-V1" {
        return Err("invalid input header".to_string());
    }

    let mut id = String::new();
    let mut question = String::new();
    let mut budget = 0usize;
    let mut lookups = Vec::new();
    let mut fragments = Vec::new();

    for raw_line in lines {
        let line = raw_line.trim_end_matches('\r');
        if line.is_empty() {
            continue;
        }
        let mut fields = line.splitn(3, '\t');
        let kind = fields.next().unwrap_or("");
        let first = fields
            .next()
            .ok_or_else(|| "record is missing tab separators".to_string())?;
        match kind {
            "fragment" => {
                let text = fields
                    .next()
                    .ok_or_else(|| "fragment record requires address and text".to_string())?;
                fragments.push(Fragment {
                    address: unescape(first)?,
                    text: unescape(text)?,
                    score: 0,
                    token_count: 0,
                });
            }
            "lookup" => lookups.push(unescape(first)?),
            "id" => id = unescape(first)?,
            "question" => question = unescape(first)?,
            "budget" => {
                budget = first
                    .parse::<usize>()
                    .map_err(|_| "budget must be a positive integer".to_string())?;
                if budget == 0 {
                    return Err("budget must be a positive integer".to_string());
                }
            }
            _ => return Err("unknown record type".to_string()),
        }
    }

    if id.is_empty() || question.is_empty() || budget == 0 || fragments.is_empty() {
        return Err("fixture requires id, question, positive budget, and fragments".to_string());
    }
    let mut addresses = HashSet::with_capacity(fragments.len());
    for fragment in &fragments {
        if !addresses.insert(fragment.address.clone()) {
            return Err("duplicate fragment address".to_string());
        }
    }
    Ok(Input {
        id,
        question,
        budget,
        lookups,
        fragments,
    })
}

fn words(text: &str) -> Vec<String> {
    let mut output = Vec::new();
    let mut word = String::new();
    for ch in text.chars() {
        if ch.is_ascii_alphanumeric() {
            word.push(ch.to_ascii_lowercase());
        } else if !word.is_empty() {
            output.push(std::mem::take(&mut word));
        }
    }
    if !word.is_empty() {
        output.push(word);
    }
    output
}

fn truncate_to_budget(value: &str, budget: usize) -> String {
    let bytes = value.as_bytes();
    let mut count = 0usize;
    let mut in_word = false;
    for (index, byte) in bytes.iter().enumerate() {
        let word = byte.is_ascii_alphanumeric();
        if word && !in_word {
            count += 1;
            if count == budget {
                let mut end = index + 1;
                while end < bytes.len() && bytes[end].is_ascii_alphanumeric() {
                    end += 1;
                }
                return value[..end].to_string();
            }
        }
        in_word = word;
    }
    value.to_string()
}

fn run(
    input: &str,
    started: Instant,
    strategy: &str,
) -> Result<(Output, OperationMetrics), String> {
    let mut metrics = OperationMetrics::default();
    let parsed = parse(input)?;
    metrics.input_parse_ns = started.elapsed().as_nanos();

    let question_tokens = words(&parsed.question).len();
    let mut fragments = parsed.fragments;
    if strategy == "baseline" {
        let assembly_started = Instant::now();
        let original_source_tokens = fragments
            .iter()
            .map(|fragment| words(&fragment.text).len())
            .sum();
        let source = fragments
            .iter()
            .map(|fragment| fragment.text.as_str())
            .collect::<Vec<_>>()
            .join(" ");
        let context = truncate_to_budget(&source, parsed.budget);
        let context_tokens = words(&context).len();
        metrics.expansion_assembly_ns = assembly_started.elapsed().as_nanos();
        return Ok((
            Output {
                input_id: parsed.id,
                original_source_tokens,
                question_tokens,
                retrieved_addresses: Vec::new(),
                lookups: Vec::new(),
                expanded: Vec::new(),
                context,
                context_tokens,
                elapsed_ns: started.elapsed().as_nanos(),
            },
            metrics,
        ));
    }
    let retrieval_started = Instant::now();
    let query: HashSet<String> = words(&parsed.question).into_iter().collect();
    let mut original_source_tokens = 0usize;
    for fragment in &mut fragments {
        let fragment_words = words(&fragment.text);
        fragment.token_count = fragment_words.len();
        original_source_tokens += fragment.token_count;
        let terms: HashSet<String> = fragment_words.into_iter().collect();
        fragment.score = query.intersection(&terms).count();
    }
    let mut ranked: Vec<usize> = fragments
        .iter()
        .enumerate()
        .filter_map(|(index, item)| if item.score > 0 { Some(index) } else { None })
        .collect();
    ranked.sort_by(|left, right| {
        fragments[*right]
            .score
            .cmp(&fragments[*left].score)
            .then_with(|| {
                fragments[*left]
                    .address
                    .as_bytes()
                    .cmp(fragments[*right].address.as_bytes())
            })
    });
    metrics.retrieval_ns = retrieval_started.elapsed().as_nanos();

    let lookup_started = Instant::now();
    let address_map: HashMap<String, String> = fragments
        .iter()
        .map(|fragment| (fragment.address.clone(), fragment.text.clone()))
        .collect();
    let lookups = parsed
        .lookups
        .iter()
        .map(|address| Lookup {
            address: address.clone(),
            text: address_map.get(address).cloned(),
        })
        .collect();
    metrics.address_lookup_ns = lookup_started.elapsed().as_nanos();

    let assembly_started = Instant::now();
    let mut context_tokens = 0usize;
    let mut expanded = Vec::new();
    let mut context_parts = Vec::new();
    let retrieved_addresses = ranked
        .iter()
        .map(|index| fragments[*index].address.clone())
        .collect();
    for index in ranked {
        let fragment = &fragments[index];
        if context_tokens + fragment.token_count > parsed.budget {
            continue;
        }
        context_tokens += fragment.token_count;
        context_parts.push(fragment.text.clone());
        expanded.push((fragment.address.clone(), fragment.text.clone()));
    }
    let context = context_parts.join(" ");
    metrics.expansion_assembly_ns = assembly_started.elapsed().as_nanos();

    Ok((
        Output {
            input_id: parsed.id,
            original_source_tokens,
            question_tokens,
            retrieved_addresses,
            lookups,
            expanded,
            context,
            context_tokens,
            elapsed_ns: started.elapsed().as_nanos(),
        },
        metrics,
    ))
}

fn json_string(value: &str) -> String {
    let mut output = String::with_capacity(value.len() + 2);
    output.push('"');
    for ch in value.chars() {
        match ch {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{08}' => output.push_str("\\b"),
            '\u{0C}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            ch if ch < '\u{20}' => output.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => output.push(ch),
        }
    }
    output.push('"');
    output
}

fn serialize(output: &Output) -> String {
    let addresses = output
        .retrieved_addresses
        .iter()
        .map(|item| json_string(item))
        .collect::<Vec<_>>()
        .join(",");
    let lookups = output
        .lookups
        .iter()
        .map(|item| {
            let text = item
                .text
                .as_ref()
                .map(|value| json_string(value))
                .unwrap_or_else(|| "null".to_string());
            format!(
                "{{\"address\":{},\"text\":{}}}",
                json_string(&item.address),
                text
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    let expanded = output
        .expanded
        .iter()
        .map(|(address, text)| {
            format!(
                "{{\"address\":{},\"text\":{}}}",
                json_string(address),
                json_string(text)
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"input_id\":{},\"original_source_tokens\":{},\"question_tokens\":{},\"retrieved_addresses\":[{}],\"lookups\":[{}],\"expanded\":[{}],\"context\":{},\"context_tokens\":{},\"elapsed_ns\":{}}}",
        json_string(&output.input_id), output.original_source_tokens, output.question_tokens,
        addresses, lookups, expanded, json_string(&output.context), output.context_tokens, output.elapsed_ns
    )
}

fn run_cli() -> Result<(), String> {
    let started = Instant::now();
    let args: Vec<String> = env::args().collect();
    let strategy = args.get(2).map(String::as_str).unwrap_or("asm");
    if strategy != "asm" && strategy != "baseline" {
        return Err("strategy must be asm or baseline".to_string());
    }
    let source = if let Some(path) = args.get(1) {
        fs::read_to_string(path).map_err(|_| "could not read benchmark fixture".to_string())?
    } else {
        let mut source = String::new();
        io::stdin()
            .read_to_string(&mut source)
            .map_err(|_| "could not read benchmark input".to_string())?;
        source
    };
    let (output, mut metrics) = run(&source, started, strategy)?;
    let serialization_started = Instant::now();
    let serialized = serialize(&output);
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(serialized.as_bytes())
        .map_err(|_| "could not write benchmark output".to_string())?;
    stdout
        .write_all(b"\n")
        .map_err(|_| "could not write benchmark output".to_string())?;
    stdout
        .flush()
        .map_err(|_| "could not flush benchmark output".to_string())?;
    metrics.serialization_ns = serialization_started.elapsed().as_nanos();
    eprintln!(
        "{}{{\"input_parse_ns\":{},\"retrieval_ns\":{},\"address_lookup_ns\":{},\"expansion_assembly_ns\":{},\"serialization_ns\":{}}}",
        METRIC_PREFIX, metrics.input_parse_ns, metrics.retrieval_ns, metrics.address_lookup_ns,
        metrics.expansion_assembly_ns, metrics.serialization_ns
    );
    Ok(())
}

fn main() {
    if let Err(error) = run_cli() {
        eprintln!("{error}");
        process::exit(1);
    }
}
