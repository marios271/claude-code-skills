# agy-bridge

A MCP server which gives Claude Code a tool to delegate to Antigravity CLI.
This MCP server makes the `agy_ask` tool available to Claude Code, which it can use to prompt Antigravity CLI.

This is useful for saving tokens on things such as codebase exploration, as models like Gemini 3.5 Flash are
capable and token-efficient, and at the time of writing, also usable for free.

 > **DISCLAIMER:** This MCP server is written for windows. It will not work on Linux. If you want to use it on Linux, feel free to port it yourself (its probably 2-3 small changes if at all) and I'd love it if you opened a PR to add a `agy-bridge-linux` version! ;)


## Setup and Installation

To install this MCP server, simply copy and paste this directory (`agy-bridge`)
into `~/.claude/mcp-servers`.

Then install the required npm dependencies:

```bash
cd ~/.claude/mcp-servers/agy-bridge
npm install
```

 > **Note:** `node-pty` requires native   compilation. Make sure you have the Windows C++ build tools installed. If the install fails, run `npm install --global windows-build-tools` first (requires an elevated prompt), or install the "Desktop development with C++" workload from Visual Studio.

After installing, run the following command to register the MCP server with Claude Code:

```bash
claude mcp add agy-bridge --transport stdio --scope user -- node ~/.claude/mcp-servers/agy-bridge/agy-bridge.js
```


## Additional Resources

If you are installing this to be able to save tokens by using Antigravity CLI for things like
codebase investigation, append the following into your global `CLAUDE.md` (`~/.claude/CLAUDE.md`):

```markdown
## agy_ask (Antigravity CLI)
You have access to the `agy_ask` MCP tool which delegates tasks to Antigravity CLI.
 
### Step 1 — Always read the directory tree first (never via agy_ask)
Before any exploration task, read the directory tree yourself using your own tools (e.g. `list_directory`, `tree`, or equivalent). This costs almost nothing and lets you build a precise, targeted prompt for agy_ask, minimizing the number of agy_ask calls needed.
 
### Step 2 — Decide: read directly or delegate to agy_ask
 
**Read files directly (your own tools) when:**
- The task touches **1–2 files** — direct reads are cheaper than agy_ask overhead
- You already know the exact file path and need a quick look
- You are writing or editing code (always use your own tools for writes)
**Use agy_ask when:**
- The task touches **3 or more files**, or you don't yet know which files are relevant
- The task requires tracing logic, understanding structure, or summarizing large sections of code
- Any research where you would otherwise open more than 2 files to get the answer
The fixed cost of one agy_ask call (invocation overhead + response formatting) is roughly equivalent to reading 2–3 small files directly. Below that threshold, agy_ask wastes tokens; above it, agy_ask saves them.
 
### What agy_ask is NOT for
- Do not use it to offload critical thinking (bug analysis, design decisions) — do that yourself
- Do not use it when the directory tree already tells you exactly which 1–2 files to read
```