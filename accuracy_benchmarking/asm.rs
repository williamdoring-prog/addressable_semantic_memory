use std::collections::HashSet;

pub struct Fragment {
    pub address: &'static str,
    pub text: &'static str,
}

pub struct ASM {
    pub question: &'static str,
    pub fragments: Vec<Fragment>,
    pub budget: usize,
}

fn words(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut current = String::new();
    for c in text.chars() {
        if c.is_ascii_alphanumeric() {
            current.push(c.to_ascii_lowercase());
        } else if !current.is_empty() {
            out.push(std::mem::take(&mut current));
        }
    }
    if !current.is_empty() { out.push(current); }
    out
}

fn json_escaped(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000C}' => out.push_str("\\f"),
            _ => out.push(c),
        }
    }
    out
}

impl ASM {
    /// Computes ranking and bounded selection and serializes the shared JSON
    /// document. Performs no I/O so calls can be timed cleanly.
    pub fn run(&self) -> String {
        let query: HashSet<String> = words(self.question).into_iter().collect();
        let mut original_words = 0usize;
        let mut ranked: Vec<(usize, String, usize, usize)> = Vec::new();

        for (index, fragment) in self.fragments.iter().enumerate() {
            let fragment_words = words(fragment.text);
            let count = fragment_words.len();
            original_words += count;
            let terms: HashSet<String> = fragment_words.into_iter().collect();
            let score = query.intersection(&terms).count();
            if score > 0 {
                ranked.push((score, fragment.address.to_string(), count, index));
            }
        }

        ranked.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));

        let mut context_words = 0usize;
        let mut context_parts: Vec<&str> = Vec::new();
        let mut selected = Vec::new();
        for (score, address, count, index) in &ranked {
            if context_words + *count > self.budget { continue; }
            context_words += *count;
            context_parts.push(self.fragments[*index].text);
            selected.push(format!(
                "{{\"address\":\"{}\",\"score\":{}}}",
                json_escaped(address),
                score
            ));
        }

        let addresses = ranked.iter()
            .map(|(_, address, _, _)| format!("\"{}\"", json_escaped(address)))
            .collect::<Vec<_>>().join(",");

        format!(
            "{{\"original_source_words\":{},\"question_words\":{},\"retrieved_addresses\":[{}],\"selected\":[{}],\"context\":\"{}\",\"context_words\":{}}}",
            original_words,
            words(self.question).len(),
            addresses,
            selected.join(","),
            json_escaped(&context_parts.join(" ")),
            context_words
        )
    }
}
