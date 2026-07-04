---
id: shim-files-point-to-agents-md
title: Harness rule files are pointers to AGENTS.md, never content
tags: [conventions, agents, source-of-truth]
related: [handoffs-are-files]
adr: ["0001"]
confidence: high
sources: ["CLAUDE.md", "GEMINI.md", ".cursor/rules/agents.mdc", ".github/copilot-instructions.md"]
updated: 2026-07-03
---

CLAUDE.md, GEMINI.md, `.cursor/rules/agents.mdc` and
`.github/copilot-instructions.md` each contain only a pointer (or `@` import)
to AGENTS.md. All durable guidance lives in AGENTS.md alone.

If a rule needs changing, change AGENTS.md. Content appearing in a shim
beyond the pointer is a bug - move it into AGENTS.md and restore the shim.
