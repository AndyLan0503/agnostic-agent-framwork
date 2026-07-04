# Knowledge base

One fact per card. Short, searchable, cross-linked, citable. Grep here before
asking; update the card in the same PR that changes the fact.

## Card format

```markdown
---
id: <filename-without-md, kebab-case>
title: <the fact, as a sentence>
tags: [<topic>, <topic>]
related: [<other-card-id>]
adr: ["NNNN"]              # decision records backing this fact, if any
confidence: high | medium | low
sources: ["<file or glob that proves the claim>"]
updated: YYYY-MM-DD
---

Two or three short paragraphs or bullets. State the fact, the enforcement or
evidence, and anything a reader would otherwise get wrong.
```

## Conventions

- **One fact per card.** A card that needs sections is two cards.
- **confidence: high** means verified against the sources and, where it is a
  decision, ADR-backed. Anything softer is medium or low.
- **sources** point at the code that proves the claim, so staleness is
  checkable.
- When the fact changes, update the card and its `updated` date in the same
  PR - a stale card is worse than no card.

## Index

- [shim-files-point-to-agents-md](shim-files-point-to-agents-md.md) - harness rule files are pointers, never content
- [handoffs-are-files](handoffs-are-files.md) - anything worth keeping from a session lives in a committed file
- [gnhf-safe-subcommands](gnhf-safe-subcommands.md) - criterion for green-flagging subcommands of blocked tools in unattended runs
