# ASM Schemas

Function-calling tool definitions for the 8 ASM operations. These schemas
bind to the ASM runtime so any LLM harness (OpenAI, Anthropic, JSON Schema)
can import and bind them as tools.

Available exports:
- tool_schema(style, tool_id) — get the schema for a specific tool
- TOOL_SCHEMAS — dict of all 8 tool schemas keyed by tool_id