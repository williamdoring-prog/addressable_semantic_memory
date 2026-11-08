# ASM Directory Structure

```text
ASM/
├── .gitignore
├── README.md
├── AGENTS.md
├── PROJECT_PLAN.md
├── ARCHITECTURE.md
├── ASM_SPECIFICATION.md
├── BENCHMARK_PROTOCOL.md
├── LANGUAGE_BENCHMARKS.md
├── WEB_INTERFACE.md
├── DIRECTORY_STRUCTURE.md
├── WORK_QUEUE.md
├── app/
│   ├── interface/          # Browser interface
│   └── controller/         # Experiment controller, separate from the interface
├── asm/                    # Language-independent ASM engine
├── benchmarks/
│   ├── c/
│   ├── go/
│   ├── rust/
│   ├── fixtures/
│   │   ├── datasets/
│   │   ├── inputs/
│   │   └── expected_outputs/
│   ├── formats/            # Shared benchmark data formats
│   ├── operations/
│   ├── scenarios/
│   └── schemas/
├── tests/
├── data/
│   ├── corpus/              # Original source and corpus data
│   └── results/             # Persisted experiment results
└── docs/                    # Supplementary material generated during the project
```

## Documentation rules

- Keep authoritative specifications and plans at the repository root; do not duplicate them under `docs/`.
- Update the root specification directly when its requirements change.
- Link supplementary documents to the relevant root specification.
- Keep experimental findings separate from planned or expected results.
- Preserve historical research reports rather than silently replacing them.

## Directory conventions

- Keep original corpus data separate from generated benchmark results.
- Keep shared benchmark fixtures and formats outside language-specific benchmark directories so implementations can use the same inputs and definitions.
- Keep the browser interface and experiment controller in separate modules under `app/`.
- `.gitkeep` files preserve otherwise-empty directories in version control until they contain project files.
