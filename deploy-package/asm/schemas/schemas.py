"""
Function-calling tool definitions for the 8 ASM operations.

Each schema defines the parameters an LLM harness can bind as a function call.
The actual implementation is provided by the ASM runtime (deploy-package/asm/core/asm.py
and deploy-package/asm/tools/tools.py). The schemas are stable — their parameter
signatures do not change, ensuring agent bindings remain valid across versions.
"""

import json

from asm.tools.tools import _coerce_budget, ToolError

#: All 8 ASM tool schemas, keyed by tool_id
TOOL_SCHEMAS = {
    "asm.create_scope": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Create a new bounded semantic context (scope). "
                "Initializes an empty scope with optional parent and initial context."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier for the new scope (e.g. 'project/setup')"
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Brief description of the scope's purpose"
                    },
                    "initial_context": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "address": {"type": "string"},
                                "text": {"type": "string"}
                            },
                            "required": ["address", "text"]
                        },
                        "description": "Optional initial units to populate the scope with",
                        "default": []
                    },
                    "parent_scope": {
                        "type": ["string", "null"],
                        "description": "Optional identifier of a parent scope for hierarchical organization",
                        "default": None
                    }
                },
                "required": ["scope_id", "purpose"],
            }
        }
    },
    "asm.add": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Add information to an existing scope. Preserves semantic information "
                "and creates addressable context where appropriate."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope to add information to"
                    },
                    "address": {
                        "type": "string",
                        "description": "Stable address for the new unit (e.g. 'feature/login-page')"
                    },
                    "text": {
                        "type": "string",
                        "description": "The content/information to add to the scope"
                    },
                    "parent": {
                        "type": ["string", "null"],
                        "description": "Optional parent address within the scope for nested organization",
                        "default": None
                    }
                },
                "required": ["scope_id", "address", "text"],
            }
        }
    },
    "asm.query": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Retrieve the most relevant context for a query under a word budget. "
                "Prefers the smallest useful amount of context."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope to query within"
                    },
                    "question": {
                        "type": "string",
                        "description": "The task query, single line"
                    },
                    "budget": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "WORD budget (rule R4), never tokens"
                    },
                    "abstraction_depth": {
                        "type": "integer",
                        "description": "Depth of abstraction to search (default: 0 = full scope)"
                    }
                },
                "required": ["scope_id", "question", "budget"],
            }
        }
    },
    "asm.get": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Retrieve deeper information using an address or context identifier. "
                "Supports multiple abstraction levels where the underlying information is available."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope containing the address"
                    },
                    "address": {
                        "type": "string",
                        "description": "Stable unit ID to resolve (section 6.1)"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Abstraction depth (0 = direct unit, higher = deeper detail)",
                        "minimum": 0,
                        "default": 0
                    }
                },
                "required": ["scope_id", "address"],
            }
        }
    },
    "asm.inspect": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Inspect the health of the active scope. Identifies conditions such as "
                "scope being too broad/narrow, unrelated topics mixed together, stale "
                "summaries, missing context, conflicting information, and more. "
                "This is a critical feature."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope to inspect"
                    },
                    "address": {
                        "type": ["string", "null"],
                        "description": "Optional: focus inspection on a specific address within the scope",
                        "default": None
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Level of detail for the inspection report",
                        "default": "medium"
                    }
                },
                "required": ["scope_id"],
            }
        }
    },
    "asm.adjust_scope": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Allow an agent to adjust context boundaries. Support operations: split, "
                "merge, narrow, broaden, rebuild. Do not silently destroy context."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope to adjust"
                    },
                    "address": {
                        "type": "string",
                        "description": "Address or boundary to operate on"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["split", "merge", "narrow", "broaden", "rebuild"],
                        "description": "The adjustment operation to perform"
                    },
                    "preserve": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Addresses or summaries to preserve through the adjustment",
                        "default": []
                    }
                },
                "required": ["scope_id", "address", "operation"],
            }
        }
    },
    "asm.summarize": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Create or update a compressed working representation of a scope. "
                "The summary preserves references to deeper addressable information "
                "whenever possible."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope to summarize"
                    },
                    "budget": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "WORD budget for the summary"
                    },
                    "focus": {
                        "type": "string",
                        "description": "Optional focus topic to prioritize in the summary",
                        "default": ""
                    }
                },
                "required": ["scope_id", "budget"],
            }
        }
    },
    "asm.recover": {
        "type": "function",
        "function": {
            "name": "asm",
            "description": (
                "Provide a context recovery workflow for an agent that suspects it has "
                "lost track of the project or current task. Helps the agent inspect the "
                "active scope, identify missing/conflicting context, retrieve relevant "
                "summaries and deeper detail, and rebuild a coherent working context."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scope_id": {
                        "type": "string",
                        "description": "Identifier of the scope to recover"
                    },
                    "check_active": {
                        "type": "boolean",
                        "description": "Whether to inspect the current active scope first",
                        "default": True
                    },
                    "rebuild": {
                        "type": "boolean",
                        "description": "Whether to attempt full context rebuild",
                        "default": True
                    }
                },
                "required": ["scope_id"],
            }
        }
    }
}


def tool_schema(tool_id, style="openai"):
    """Return the function-calling tool schema for the given tool_id and style.

    Args:
        tool_id: One of the 8 tool_ids in TOOL_SCHEMAS.
        style: One of "openai", "anthropic", "jsonschema". Defaults to "openai".

    Returns:
        A tool definition dict compatible with the given style.

    Raises:
        ToolError: If tool_id is not recognized or style is unsupported.
    """
    if tool_id not in TOOL_SCHEMAS:
        raise ToolError("invalid_tool_id",
                        f"unknown tool_id: {tool_id}. "
                        f"Must be one of: {', '.join(TOOL_SCHEMAS.keys())}")
    schema = TOOL_SCHEMAS[tool_id]
    if style == "openai":
        return {
            "type": "function",
            "function": {
                "name": "asm",
                "description": schema["function"]["description"],
                "parameters": schema["function"]["parameters"]
            }
        }
    if style == "anthropic":
        return {
            "name": "asm",
            "description": schema["function"]["description"],
            "input_schema": schema["function"]["parameters"]
        }
    if style == "jsonschema":
        return schema["function"]["parameters"]
    raise ToolError("invalid_format",
                    f"unknown schema style: {style}. Must be one of: openai, anthropic, jsonschema")