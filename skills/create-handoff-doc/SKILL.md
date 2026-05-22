---
name: create-handoff-doc
model: claude-haiku-4-5
description: >
  Creates a handoff document for resuming session progress in future Claude Code Sessions
---

# Handoff Document Skill

This skill is used to create a handoff markdown document from this Claude Code session.
The handoff document will be used to resume later Claude Code sessions with fresh context.

- Produce a markdown file named HANDOFF-YYYY-MM-DD.md
- Refer to assets/example-handoff-doc.md for an example handoff document structure
- Place the file in the project root

Use the following instructions for this task:

## What to collect from the user
Ask (or infer from context) these key pieces:
1. **Project/system name** and one-line description
2. **Current status** — what's done, what's in progress
3. **Open issues or blockers**
4. **Gotchas / tribal knowledge** — things not written down
5. **Recommended next steps** - both from yours as well as the user's suggestions
Do not provide an "Other" option in the question prompt. The Claude Code interface will automatically add this.

## Output structure
Produce a document with these sections:
- Executive Summary
- Current Status
- Architecture / How It Works (if technical)
- Open Items & Blockers
- Gotchas & Tribal Knowledge
- Failed Attempts
- Recommended Next Steps

## Format
- Use clear headings, tables for contacts/links, and bullet points for lists
- Tone: professional but readable — written for someone coming in cold