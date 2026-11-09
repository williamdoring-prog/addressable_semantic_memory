# ASM — Addressable Semantic Memory

Deployable package for integrating Addressable Semantic Memory into AI projects.

## Overview

ASM helps an AI agent manage bounded semantic context by organizing information into
scopes (project architecture, subsystems, features, bug investigations, migrations,
deployment, current task). Each scope supports multiple levels of abstraction and
addressable retrieval of deeper detail.

Agents can create scopes, add information, query for relevant context, inspect the
active scope, adjust boundaries, create summaries, and recover from context loss —
all without needing to load an entire project's context.

## Quick Start

1. Copy the `asm/` directory into your project.
2. Register `tool-registry.json` with your agent/tool system.
3. Initialize ASM scopes relevant to your project.
4. Invoke ASM tools (`serve`, `list`, `inspect`) under a word budget.

## Contents

- `asm/` — ASM runtime core, documentation, and tool interfaces
- `tool-registry.json` — stable tool handles for ASM operations