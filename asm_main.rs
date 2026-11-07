mod asm;
use asm::{ASM, Fragment};
use std::time::Instant;

fn main() {
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
