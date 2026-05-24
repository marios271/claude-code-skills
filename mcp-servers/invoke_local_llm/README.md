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


## Model Setup

First, pull the model of your choice (here using `qwen2.5:14b`):

```bash
ollama pull qwen2.5:14b
```

Then, create the optimized local model.
Create a file called `Modelfile` and set your preferences there:

```
FROM qwen2.5:14b           # Which model to use (e.g. gemma4:e4b, qwen2.5:14b, ...)
PARAMETER num_gpu 40       # How many layers of the LLM to load into VRAM rather than RAM
PARAMETER num_ctx 32768    # The context window (here: 32k)
```

After, run this command to register the model with ollama:

```bash
ollama create qwen14b-explorer -f Modelfile
```

You can use whatever name you want here. Make sure to also set the exact same name in `main.py` later.
At the end, `Modelfile` can be deleted.


> `num_gpu 40` and `num_ctx 32768` are tuned for an RTX 4050 laptop (6GB VRAM) with RAM spillover.
> Adjust them based on your GPU. Run `ollama ps` after a call to verify VRAM usage.


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

### Step 1 — Always read the directory tree first (never via invoke_local_llm)
Before any exploration task, read the directory tree yourself using your own tools. This costs almost nothing and lets you build a precise, targeted prompt for invoke_local_llm, minimizing the number of calls needed.

### Step 2 — Decide: read directly or delegate to invoke_local_llm

**Read files directly (your own tools) when:**
- The task touches **1–2 files** — direct reads are cheaper than invoke_local_llm overhead
- You already know the exact file path and need a quick look
- You are writing or editing code (always use your own tools for writes)

**Use invoke_local_llm when:**
- The task touches **3 or more files**, or you don't yet know which files are relevant
- The task requires tracing logic across the codebase, understanding structure, or summarizing large sections
- Any research where you would otherwise open more than 2 files to get the answer

The fixed cost of one invoke_local_llm call (model load + agent loop + response) is roughly equivalent to reading 2–3 small files directly. Below that threshold, invoke_local_llm wastes tokens; above it, it saves them.

### Calling invoke_local_llm
Always pass the most specific prompt you can — the better the prompt, the fewer internal tool calls the local model needs.
- `allowed_dirs`: pass only the project root(s) relevant to the task
- `max_steps`: omit for default (30); lower it (e.g. 10) for simple lookups

### What invoke_local_llm is NOT for
- Do not use it to offload critical thinking (bug analysis, design decisions) — do that yourself
- Do not use it when the directory tree already tells you exactly which 1–2 files to read
- Do not use it for writes, edits, or anything requiring your own judgment

### Example
If the user gives a prompt like this:
> look into the current structure and determine how to best do the login sequence (explore a little for that)
You should **NOT** use your own exploration tools. In this scenario, you should **ALWAYS** delegate to `invoke_local_llm`.

For a prompt like this:
> can you try fixing this bug in the auth routine? i believe it to be invalid return data in either file1 or file2
You should FIRST read the two files using your own tools and analyze them. If they seem to be free of issues, then ask the user
if they want you to explore in order to find the bug. If the user confirms, then explore **using `invoke_local_llm`**.

### Rule of Thumb
Anytime you would use your own explore tools or summon an explore agent using your builtin tools, should **MUST NOT** do that.
Instead, delegate to `invoke_local_llm`.
```
