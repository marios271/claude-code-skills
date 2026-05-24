# invoke_local_llm

An MCP server that gives Claude Code a tool to delegate tasks to a local Ollama model.
This MCP server makes the `invoke_local_llm` tool available to Claude Code, which it can use to offload
multi-file exploration tasks to a locally running LLM , which saves Claude Code tokens on things like repetitive filesystem work.

> **Note:** This server is written for Windows and tested with the Ollama desktop app. It should work on Linux/macOS
> with no changes, but has not been tested there.



## Prerequisites

- [Ollama](https://ollama.com) installed and running
- The `qwen14b-explorer` model set up (see below)
- Python 3.10+



## Configuring the local LLM

In `main.py`, there are four fields:

```python
MODEL_TO_USE = "qwen2.5:7b"
KEEP_ALIVE_TIMEOUT = "30s"
LAYERS_ON_GPU = 9999
CONTEXT_WINDOW = 32768
```

Here's what each one means:
- `MODEL_TO_USE`: The model to use. Pick it out at the ollama registry and pull it using `ollama pull <model-name>`
- `KEEP_ALIVE_TIMEOUT`: How long after the model is finished to wait before unloading it. Keep this over at least ~20s, as in between tool calls the model is idle. Example: keep alive is 5s, the tool call takes 10s, the model unloads before the tool call finished and the model has to be loaded again.
- `LAYERS_ON_GPU`: How many layers of the LLM to run on the GPU (to run all, use a very large number like 9999)
- `CONTEXT_WINDOW`: Size of the LLM's context window (how much information it can "hold")

> **Important:** If you choose a too powerful model or try to put too much load onto the gpu,
> ollama may silently block execution (infinite wait loop).



## Installation

Copy this directory into `~/.claude/mcp-servers`.
Then, install dependencies:

```bash
pip install mcp ollama
```

Register the MCP server with Claude Code:

```bash
claude mcp add ollama-explorer --transport stdio --scope user -- python ~/.claude/mcp-servers/ollama-explorer/mcp_explorer.py
```



## Additional Resources

If you want to instruct Claude Code to use this for codebase exploration, append this to your global `CLAUDE.md` (`~/.claude/CLAUDE.md`):

```markdown
## invoke_local_llm (Local LLM Explorer)

You have access to the `invoke_local_llm` MCP tool which delegates filesystem exploration tasks to a local LLM running on Ollama.

---

### The two phases — always identify them before doing anything

Most codebase prompts contain one or both of:

- **Exploration phase** — "get an understanding of X", "see how Y works", "find where Z is implemented". Open-ended; you do not yet know which files matter.
- **Targeted phase** — "then check these files", "then tell me if README and CLAUDE.md agree". Closed; specific named files, specific facts.

Identify which phases are present before touching any tool. The phases use different tools and must never be collapsed into one step.

---

### Exploration phase — invoke_local_llm, always, no exceptions

If the prompt contains an exploration phase, you **must** call `invoke_local_llm`. This is not a judgment call. Do not substitute:
- reading the directory tree
- glob/pattern searching
- reading a few files yourself and deciding you "have enough"

The directory tree and search results are inputs to writing a good `invoke_local_llm` prompt — they are not a replacement for delegation. Seeing familiar file names in the tree does not mean you understand the codebase well enough to skip exploration.

**What to ask the local LLM for:** raw facts only — file paths, line numbers, function names, call sites, module structure, what a module exports. Never ask it to compare files, find inconsistencies, draw conclusions, or make recommendations. That is your job.

---

### Targeted phase — read directly yourself, always

Named files in the prompt are always read directly by you — even when the task also has an exploration phase. After `invoke_local_llm` returns, read the named files with your own tools and do all reasoning yourself.

Do not include named target files in the `invoke_local_llm` prompt. The local LLM explores; you analyze.

---

### Directory listing — exclude build artifacts first

Before listing, always exclude build output and dependency directories. These commonly fill result caps entirely with useless files before a single source file appears.

**Always exclude:** `target/`, `node_modules/`, `dist/`, `build/`, `.git/`, `__pycache__/`, `*.o`, `*.d`, `*.rlib`, `*.rmeta`

If the project root listing comes back dominated by build artifacts, narrow the search to the actual source directories rather than accepting a useless result. If `.gitignore` or `.claudeignore` are present, skim them first to catch project-specific exclusions. The goal is that your listing reflects actual source structure, not build artifacts.

---

### Calling invoke_local_llm

- Write the most specific prompt you can after reading the directory tree — fewer internal steps needed means faster, more accurate results
- `allowed_dirs`: project root(s) only
- `max_steps`: 5–10 for focused reads; 15–20 for broad codebase traces
- Ask for facts, not analysis

---

### Decision table

| Situation | Action |
|---|---|
| Prompt has an exploration phase | Call `invoke_local_llm` — mandatory |
| Prompt has a targeted phase (named files) | Read those files directly yourself |
| Prompt has both phases | Call `invoke_local_llm` for exploration; then read named files directly |
| 1–2 named files, no exploration phase | Read directly, skip `invoke_local_llm` |
| Writing or editing code | Always direct |

---

### Avoid double-cost failure

If `invoke_local_llm` returns weak results and you re-read files yourself anyway, you paid both costs. Mitigate:
- Verify critical facts (API signatures, constants) with a direct read after delegation
- If a task is borderline (small, fully named, no understanding phase), default to direct reads

---

### Examples

**Exploration + targeted (the common compound case):**
> get an understanding of the codebase and then check whether README, CLAUDE.md, and CONTRIBUTING.md are consistent

1. List directories (excluding build artifacts) to orient yourself
2. Call `invoke_local_llm` — ask for codebase structure, module layout, build system, current feature state. Do not mention README/CLAUDE.md/CONTRIBUTING.md in this call.
3. Read README, CLAUDE.md, and CONTRIBUTING.md directly yourself
4. Reason about consistency yourself and report to the user

**Exploration only:**
> how does the memory allocator work

1. List directories
2. Call `invoke_local_llm` — ask for file paths, function names, and call sites related to memory allocation

**Targeted only:**
> is there a bug in file1 or file2

No exploration phase. Read both files directly and analyze yourself.

---

### One-line rule

`invoke_local_llm` answers *"what is in the codebase"*. You answer *"what does it mean"*.
```
