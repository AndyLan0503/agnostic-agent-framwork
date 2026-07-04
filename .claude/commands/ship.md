---
description: Conduct the full SDLC pipeline for a feature request - dispatch roles, thread artifacts, pause at human gates. Never commits or pushes.
allowed-tools: Task, AskUserQuestion, Read, Edit, Write, Grep, Glob, Bash
---

Follow `skills/conduct-pipeline/SKILL.md` for this request:

$ARGUMENTS

Dispatch roles as subagents via the shims in `.claude/agents/` (they read
`roles/<name>.md`). This command adds nothing to the skill (docs/adr/0001).
