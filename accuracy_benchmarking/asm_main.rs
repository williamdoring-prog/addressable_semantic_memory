mod asm;
use asm::{ASM, Fragment};
use std::time::Instant;

/// Left-to-right scanner: \\t -> TAB, \\n -> NL, \\\\ -> backslash.
fn unescape(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = String::with_capacity(text.len());
    let mut i = 0usize;
    while i < bytes.len() {
        if bytes[i] == b'\\' && i + 1 < bytes.len() {
            match bytes[i + 1] {
                b't' => { out.push('\t'); i += 2; continue; }
                b'n' => { out.push('\n'); i += 2; continue; }
                b'\\' => { out.push('\\'); i += 2; continue; }
                _ => {}
            }
        }
        out.push(bytes[i] as char);
        i += 1;
    }
    out
}

fn leak(text: String) -> &'static str {
    Box::leak(text.into_boxed_str())
}

/* Input-file mode (challenge, WORKQUEUE W4): parsing happens before the
   timed section; asm.run() (algorithm + serialization) is the only timed
   work, identical to the other implementations. Strings are leaked into
   'static borrows because the ASM struct stores &'static str fields. */
fn run_file(path: &str, budget_arg: Option<&str>) {
    let data = std::fs::read_to_string(path).expect("cannot open input file");

    let mut lines = data.split('\n');
    let question_line = lines.next().unwrap_or("").trim_end_matches('\r');
    let question: &'static str = leak(unescape(question_line));

    let budget_line = lines.next().unwrap_or("").trim_end_matches('\r');
    let default_budget: usize = budget_line.trim().parse().unwrap_or(0);
    let budget = budget_arg
        .and_then(|value| value.trim().parse::<usize>().ok())
        .unwrap_or(default_budget);

    let fragments: Vec<Fragment> = lines
        .filter_map(|line| {
            let line = line.trim_end_matches('\r');
            if line.is_empty() {
                return None;
            }
            let tab = line.find('\t')?;
            if tab == 0 {
                return None;
            }
            Some(Fragment {
                address: leak(line[..tab].to_string()),
                text: leak(line[tab + 1..].to_string()),
            })
        })
        .collect();

    let asm = ASM { question, fragments, budget };

    // Timed: algorithm + serialization. Output happens after the timer.
    let start = Instant::now();
    let json = asm.run();
    let elapsed = start.elapsed();
    println!("{}", json);
    eprintln!("BENCHMARK_NS {}", elapsed.as_nanos());
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() >= 2 {
        run_file(&args[1], args.get(2).map(|value| value.as_str()));
        return;
    }

    let fragments = vec![
        Fragment { address: "architecture", text: "ASM uses deterministic retrieval and bounded context assembly." },
        Fragment { address: "memory", text: "Persistent memory should preserve important project state across sessions." },
        Fragment { address: "retrieval", text: "Retrieval ranks relevant fragments using question term overlap." },
        Fragment { address: "voice", text: "Voice output should remain responsive and interruptible." },
        Fragment { address: "safety", text: "Snapshots validation and rollback protect autonomous project changes." },
        Fragment { address: "research", text: "Research agents can investigate new techniques and report evidence." },
    ];

    let asm = ASM {
        question: "How does ASM retrieve relevant context and keep the context bounded?",
        fragments,
        budget: 28,
    };

    // Timed: algorithm + serialization. Output happens after the timer.
    let start = Instant::now();
    let json = asm.run();
    let elapsed = start.elapsed();
    println!("{}", json);
    eprintln!("BENCHMARK_NS {}", elapsed.as_nanos());
}
