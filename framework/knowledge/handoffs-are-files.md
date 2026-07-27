---
type: convention
title: Anything worth keeping from a session lives in a committed file
description: Session state and durable facts belong in committed files, never only in chat history.
tags: [collaboration, agents, conventions]
timestamp: 2026-07-03
id: handoffs-are-files
related: [shim-files-point-to-agents-md]
confidence: high
sources: ["AGENTS.md"]
knowform:
  direction: code-is-truth
  bindings:
    - doc_anchor: handoffs-are-files
      governs: AGENTS.md
---

Chat history evaporates at session end and is invisible to teammates and to
other harnesses. Decisions go to `framework/docs/adr/`, facts go to `framework/knowledge/`
cards (in the same PR that changes the fact), and session working state
goes to gitignored `HANDOFF.md` - written at session end, read at session
start.

If it only exists in the conversation, it does not exist for the team.
