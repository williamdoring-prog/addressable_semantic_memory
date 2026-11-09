# ASM — Addressable Semantic Memory

Core runtime for bounded semantic context management. This package helps AI agents
manage scoped context without loading entire project context.

## Contents

- `core/asm.py` — ASM class, Fragment dataclass, WORD_RE
- `tools/tools.py` — dispatch, render, load_fragments, parse_request
- `schemas/schemas.py` — function-calling tool definitions (8 tools)
- `AGENT_GUIDE.md` — when and how an AI agent should use ASM
- `ASM_SCOPE.md` — scope organization and addressable retrieval
- `INTEGRATION_GUIDE.md` — how to integrate ASM into another project

## Quick Use

```python
import sys
sys.path.insert(0, ".")
from asm.core.asm import ASM, Fragment

asm = ASM()
fragments = [
    Fragment("addr1", "some text"),
    Fragment("addr2", "more text"),
]
result = asm.run("question", fragments, 600)
print(result["context"])  # served context within budget
```