# ASM Installation

## Requirements

- Python 3.10+ (stdlib only)
- No external dependencies required for the core ASM runtime

## Installation

1. Copy the `deploy-package/` directory into your project, or add it to your Python path:

   ```bash
   cp -r deploy-package /path/to/your/project/
   ```

2. Add the `deploy-package` directory to your Python path so the `asm` module is importable:

   ```python
   import sys
   sys.path.insert(0, "deploy-package")
   import asm
   from asm import ASM, Fragment
   ```

   Or, if installed as a package:

   ```bash
   pip install -e .   # from within the project containing deploy-package/
   ```

3. Register the tool registry with your agent framework:

   ```python
   import json
   from pathlib import Path
   registry = json.loads(Path("deploy-package/tool-registry.json").read_text())
   ```

4. Initialize ASM with an addressed store. The store format is `asm_input.txt`:

   - Line 1: question (single line)
   - Line 2: default budget (integer words)
   - Lines 3+: `<address>\t<text>` (one unit per line)

   ```python
   from pathlib import Path
   from asm import ASM, Fragment

   store_path = Path("asm_input.txt")
   question = "What are the main issues with hurricane risk modeling?"
   budget = 600

   asm = ASM()
   result = asm.run(question, fragments, budget)
   ```

## Store Format

The ASM store format (`asm_input.txt`) uses tab-separated address/text pairs:

```
question text
600
doc/chunk/0001	NOAA Technical Report ...]
doc/chunk/0002	The National Environmental Satellite...]
...
```

## Verification

Confirm the ASM runtime works:

```bash
python -c "
import sys
sys.path.insert(0, 'deploy-package')
from asm import ASM, Fragment, WORD_RE
asm = ASM()
fragments = [
    Fragment('addr1', 'ASM uses deterministic retrieval and bounded context assembly.'),
    Fragment('addr2', 'Persistent memory preserves project state across sessions.'),
]
result = asm.run('How does ASM retrieve relevant context?', fragments, 100)
print(f'context_words: {result[\"context_words\"]}')
print(f'selected: {result[\"selected\"]}')
"
```