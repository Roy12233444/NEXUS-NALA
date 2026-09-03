# 🧩 Architectural Plan: NALA Modular Agent Skills & Dynamic Tool Registry

**Target Location:** `E:\NALA-Project\NALA\BACKLOG_Features\NEW_FEATURES\Modular_Agent_Skills_Architecture_Plan.md`  
**Target Path:** `core/hands/tools/` & `core/hands/tool_registry.py`  
**Status:** Advanced Implementation Specification  
**Created:** July 26, 2026  

---

## 🎯 Executive Overview

This plan defines the architectural specification for NALA’s **Modular Agent Skills Framework**. 

Rather than embedding tool execution logic directly into LLM prompts or hardcoding monolithic execution scripts, NALA decouples skill definitions into **isolated, self-contained Python modules** located in `core/hands/tools/`. 

The LLM receives only lightweight **JSON/YAML tool schemas** (name, description, parameter types). When the LLM issues a structured tool call, NALA's **`tool_registry.py`** validates the invocation against the active **`ExecutionContract` PermissionSet ($P_t$)**, executes the corresponding `.py` skill file inside the hardened Python sandbox (`sandbox.py`), and feeds the result back to the reasoning loop.

---

## 📐 System Architecture & Execution Flow

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NALA MODULAR AGENT SKILLS ARCHITECTURE                               │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                   │
│   1. MODULAR SKILL FILES (.py)           2. DYNAMIC SCHEMA GENERATOR      3. LLM CONTEXT WINDOW      │
│   ┌───────────────────────────┐         ┌───────────────────────────┐     ┌─────────────────────┐ │
│   │  core/hands/tools/        │         │   tool_registry.py        │     │  Claude 3.5 / LLaMA │ │
│   │  ├── file_manager.py      │ ──────► │  Generates lightweight    │ ──► │  Sees only lightweight│ │
│   │  ├── vector_search.py     │         │  JSON/YAML tool schemas   │     │  tool signatures    │ │
│   │  ├── python_sandbox.py    │         └───────────────────────────┘     └──────────┬──────────┘ │
│   │  └── pdf_analyzer.py      │                                                      │            │
│   └───────────────────────────┘                                                      │            │
│                                                                                      │            │
│   4. HARDENED SANDBOX EXECUTION                                                      │            │
│   ┌───────────────────────────────────────────────────────────────────────────────┐  │            │
│   │                          ACP / RCL PERMISSION CHECK                           │ ◄┘            │
│   │           Validates tool against ExecutionContract.PermissionSet (P_t)        │               │
│   └──────────────────────────────────────┬────────────────────────────────────────┘               │
│                                          │                                                        │
│                                          ▼                                                        │
│   ┌───────────────────────────────────────────────────────────────────────────────┐               │
│   │                       SANDBOX EXECUTION (sandbox.py)                          │               │
│   │     Runs target skill .py script under PEP 578 Audit Hooks & Job Objects     │               │
│   └──────────────────────────────────────┬────────────────────────────────────────┘               │
│                                          │                                                        │
│                                          ▼                                                        │
│   ┌───────────────────────────────────────────────────────────────────────────────┐               │
│   │                       RESULT FEEDBACK & LOGGING                               │               │
│   │             Returns execution output / error back to NALA Loop                │               │
│   └───────────────────────────────────────────────────────────────────────────────┘               │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Key Architectural Principles

### 1. Self-Contained Skill Files (`core/hands/tools/`)
Each agent skill lives in its own `.py` file inside `core/hands/tools/`. A skill file exposes:
* **Tool Metadata:** Name, description, category, safety level requirement (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
* **Pydantic Argument Schema:** Type-validated input arguments.
* **Execution Handler:** The `execute(args)` function that runs the logic.

```python
# Prototype Skill File: core/hands/tools/vector_search.py
from pydantic import BaseModel, Field
from core.hands.tool_registry import register_tool

class VectorSearchInput(BaseModel):
    query: str = Field(description="Semantic search query string")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to retrieve")

@register_tool(
    name="vector_search",
    description="Perform semantic search over NALA's persistent vector memory",
    category="memory",
    safety_level="LOW"
)
def execute_vector_search(args: VectorSearchInput) -> dict:
    # Actual local execution logic
    results = memory_engine.search(args.query, top_k=args.top_k)
    return {"status": "success", "results": results}
```

---

### 2. Dynamic Schema Generation (`tool_registry.py`)
* The `ToolRegistry` automatically discovers all skill modules in `core/hands/tools/` at startup.
* It inspects the `@register_tool` decorators and builds a unified OpenAI/Anthropic compatible JSON tool specification.
* **Token Efficiency:** The LLM receives only small, clean function signatures rather than hundreds of lines of implementation code!

```json
{
  "name": "vector_search",
  "description": "Perform semantic search over NALA's persistent vector memory",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Semantic search query string" },
      "top_k": { "type": "integer", "default": 5, "description": "Number of results to retrieve" }
    },
    "required": ["query"]
  }
}
```

---

### 3. ACP / RCL Permission Integration ($P_t$)
Before any skill file is executed, `ToolRegistry` queries the active `ExecutionContract`:
* Checks if `tool_name` is in `PermissionSet.allowed_tools`.
* Verifies `tool_name` is **NOT** in `PermissionSet.blocked_tools`.
* Checks filesystem glob paths (`file_read_allowlist`, `file_write_allowlist`) if the tool touches disk.
* If validation fails, execution is blocked instantly with a `SandboxViolationError`.

---

### 4. Sandboxed Execution Pipeline (`sandbox.py`)
When a skill is invoked:
1. `sandbox.py` sets up a temporary execution context.
2. Applies kernel Job Object memory/CPU limits (`sandbox_windows.py`) and PEP 578 audit hooks (`sandbox_hooks.py`).
3. Executes the skill's `execute(args)` handler in isolation.
4. Returns the result dictionary back to `nala_loop.py`.

---

## 📚 Standard NALA Skill Library Catalog

| Skill File | Name | Category | Description |
| :--- | :--- | :--- | :--- |
| `core/hands/tools/file_manager.py` | `file_manager` | Filesystem | Read, write, list, and diff workspace files securely. |
| `core/hands/tools/vector_search.py` | `vector_search` | Memory | Retrieve semantic patterns from persistent vector memory. |
| `core/hands/tools/python_sandbox.py` | `python_sandbox` | Execution | Execute isolated Python scripts inside hardened sandbox. |
| `core/hands/tools/pdf_analyzer.py` | `pdf_analyzer` | Document | Extract text, tables, and formulas from research PDFs. |
| `core/hands/tools/web_search.py` | `web_search` | Web | Fetch web documentation and search research papers. |
| `core/hands/tools/git_manager.py` | `git_manager` | Versioning | Inspect git status, create commits, and check diffs. |

---

## 📁 File Index & Directory Layout

```text
core/hands/
├── tool_registry.py            # Dynamic discovery, schema generator & permission gate
└── tools/                      # Individual Modular Skill Files
    ├── __init__.py
    ├── file_manager.py         # File read/write skill
    ├── vector_search.py        # Vector memory search skill
    ├── python_sandbox.py       # Code execution skill
    ├── pdf_analyzer.py         # PDF research paper extraction skill
    ├── web_search.py           # Web research skill
    └── git_manager.py          # Git version control skill
```

---

## 🚀 Why This Architecture Wins

1. **Unlimited Scalability:** To add a new skill (e.g. SQL Query, Docker Runner, Slack Notifier), developers simply drop a new `.py` file into `core/hands/tools/`—zero changes required in core LLM code!
2. **Maximum Token Savings:** Saves thousands of LLM context tokens by supplying concise JSON tool signatures.
3. **100% Defense-in-Depth Safety:** Every skill execution passes through ACP `PermissionSet` validation and runs inside kernel-isolated sandboxes with Windows Job Objects and PEP 578 audit hooks.
