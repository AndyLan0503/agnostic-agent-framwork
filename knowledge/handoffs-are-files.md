---
id: handoffs-are-files
title: Anything worth keeping from a session lives in a committed file
tags: [collaboration, agents, conventions]
related: [shim-files-point-to-agents-md]
adr: ["0001"]
confidence: high
sources: ["AGENTS.md", "docs/adr/0001-tool-neutral-source-of-truth.md"]
updated: 2026-07-03
---

Chat history evaporates at session end and is invisible to teammates and to
other harnesses. Decisions go to `docs/adr/`, facts go to `knowledge/`
cards (in the same PR that changes the fact), and session working state
goes to gitignored `HANDOFF.md` - written at session end, read at session
start.

If it only exists in the conversation, it does not exist for the team.
