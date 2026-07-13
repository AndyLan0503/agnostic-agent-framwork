---
type: convention
title: Harness rule files are pointers to AGENTS.md, never content
description: Harness shim files carry only a pointer to AGENTS.md; all durable guidance lives in AGENTS.md.
tags: [conventions, agents, source-of-truth]
timestamp: 2026-07-03
id: shim-files-point-to-agents-md
related: [handoffs-are-files]
adr: ["0001"]
confidence: high
sources: ["CLAUDE.md", "GEMINI.md", ".cursor/rules/agents.mdc", ".github/copilot-instructions.md"]
knowform:
  direction: code-is-truth
  bindings:
    - doc_anchor: shim-files-point-to-agents-md
      governs: CLAUDE.md
    - doc_anchor: shim-files-point-to-agents-md
      governs: GEMINI.md
    - doc_anchor: shim-files-point-to-agents-md
      governs: .cursor/rules/agents.mdc
    - doc_anchor: shim-files-point-to-agents-md
      governs: .github/copilot-instructions.md
---

CLAUDE.md, GEMINI.md, `.cursor/rules/agents.mdc` and
`.github/copilot-instructions.md` each contain only a pointer (or `@` import)
to AGENTS.md. All durable guidance lives in AGENTS.md alone.

If a rule needs changing, change AGENTS.md. Content appearing in a shim
beyond the pointer is a bug - move it into AGENTS.md and restore the shim.
