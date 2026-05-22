---
name: update-claude-md
description: Update the project CLAUDE.md file with new information, conventions, or learnings from the current session. Use this skill whenever the user says things like "add this to CLAUDE.md", "update our docs", "remember this for next time", "save this to the project memory", or when wrapping up a session and wanting to capture decisions, patterns, or commands. Also trigger when Claude notices something worth persisting (a repeated correction, a project convention, a useful command) and the user agrees it should be saved.
---

# Update CLAUDE.md

Keep the project's `CLAUDE.md` accurate and lean. Every token in that file costs context on every future run — be ruthless about brevity.

## Core principles

- **Compact over complete.** Prefer one crisp line over a paragraph. If something is obvious from the code, skip it.
- **Merge, don't append.** Find the right existing section and fold new info in. Only add a new section if nothing fits.
- **Replace stale info.** If the new content contradicts or supersedes something, remove the old entry.
- **No fluff.** No "Note:", "Important:", "Please remember to…" wrappers. State the fact directly.

## Workflow

1. **Read** the current `CLAUDE.md` (if it exists). If absent, start from scratch with minimal structure.
2. **Extract** what's worth persisting from the conversation history — decisions made, corrections given, patterns that emerged, commands that worked.
3. **Resolve gaps before writing.** If something is ambiguous or missing context:
   - Check the codebase first (relevant source files, configs, `package.json`, etc.) to ground the entry in reality.
   - If still unclear, ask the user a single focused question before proceeding.
4. **Decide placement:**
   - Fits an existing section → edit that section in-place
   - Spans multiple sections → split and place each part
   - Truly new topic → append a short new section at the bottom
5. **Write the edit.** Aim for the fewest words that convey the intent unambiguously.
6. **Check the diff mentally:** did line count grow more than necessary? If yes, trim elsewhere.

## Format rules

- Use bullet points for lists of commands or rules; prose for single-sentence facts.
- Prefer imperative voice: "Run `npm test`" not "Tests can be run with `npm test`".
- Commands go in backticks. Paths too.
- Skip section headers that only have one item — just put the item under the nearest parent.

## What belongs in CLAUDE.md

Good candidates:
- Build / test / lint commands
- Non-obvious project conventions (naming, file layout)
- Recurring gotchas that bit us in this session
- Key architecture decisions that affect everyday work

Bad candidates (leave these out):
- Things evident from reading the code
- Generic best practices that apply to every project
- Decisions that are already documented elsewhere (link instead)
- Temporary notes or TODOs

## If CLAUDE.md doesn't exist

Run `/init` instead of writing a template by hand. It inspects the actual project (files, package manager, scripts, etc.) and produces a grounded starter file. After it completes, come back to this skill to fold in whatever the current session needs to add.