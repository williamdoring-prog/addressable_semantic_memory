# ASM Scopes

ASM organizes information into explicit **scopes**. Each scope is a bounded semantic
context with a stable identifier and addressable content. Scopes support multiple
levels of abstraction and allow an AI agent to retrieve deeper detail on demand
without loading entire project context.

## Scope Concepts

### What is a Scope?

A scope is a named container for addressable information units. Each unit has:

- **address** — a stable identifier (e.g., `project/setup`, `bug/investigation`,
  `feature/login-page`, `deployment/production`)
- **text** — the content/description of that unit
- **hierarchical positioning** — optional parent/child relationships with other units

### Scope Hierarchies

Scopes can be organized hierarchically:

```
project/          (top-level scope)
  ├── setup/      (initial project configuration)
  ├── auth/       (authentication subsystem)
  │   ├── login/  (login flow)
  │   └── oauth/  (OAuth integration)
  ├── db/         (database subsystem)
  │   ├── schema/ (DB schema)
  │   └── migrations/ (migration history)
  └── deployment/ (deployment configurations)
```

### Scope Levels of Abstraction

Each scope supports multiple abstraction levels:

- **High level** — broad overview, key topics, major subsystems
- **Medium level** — subsystem details, component descriptions
- **Low level** — individual addresses, specific facts, detailed configurations

The agent can navigate between levels using `asm.get` (with `depth` parameter)
or `asm.inspect` (exact-ID resolve).

### When to Create New Scopes

Create a new scope when:

1. **Context becomes large** — project context exceeds practical serving budgets
2. **Multiple subsystems are involved** — different domain areas need separation
3. **Uncertainty about previous decisions** — need to track investigation state
4. **Conflicting information** — separate competing narratives into distinct scopes
5. **Returning after context compression** — recompress with fresh summaries
6. **Suspected loss of context** — initiate recovery protocol

### Scope Naming Conventions

- Use lowercase with `/` as delimiter: ` subsystem/feature ` or ` area/topic `
- Avoid spaces in addresses
- Prefix with domain area for clarity: `auth/`, `db/`, `deployment/`, `bug/`, `feature/`
- Consistent prefixes help agents understand scope structure at a glance

### Example Scope Workflow

1. **Create scope**: `asm.create_scope(scope_id="project/setup", purpose="Initial project configuration")`
2. **Add information**: `asm.add(scope_id="project/setup", address="db/connection", text="PostgreSQL on localhost:5432")`
3. **Query**: `asm.query(scope_id="project/setup", question="What database is used?", budget=100)`
4. **Inspect**: `asm.inspect(scope_id="project/setup", address="db/connection")`
5. **Summarize**: `asm.summarize(scope_id="project/setup", budget=200)` — creates compressed view
6. **Adjust**: `asm.adjust_scope(scope_id="project/setup", address="db/", operation="broaden")` — if scope needs more context
7. **Recover** (if lost): `asm.recover(scope_id="project/setup")` — recovery workflow