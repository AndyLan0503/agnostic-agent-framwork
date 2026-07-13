# Knowledge base

One fact per card. Short, searchable, cross-linked, citable. Grep here before
asking; update the card in the same PR that changes the fact.

## Card format

```markdown
---
type: convention | mechanism   # OKF-REQUIRED; closed vocabulary
title: <the fact, as a sentence>
description: <one-line summary>
tags: [<topic>, <topic>]
timestamp: YYYY-MM-DD
id: <filename-without-md, kebab-case>
related: [<other-card-id>]
adr: ["NNNN"]              # decision records backing this fact, if any
confidence: high | medium | low
sources: ["<file or glob that proves the claim>"]
reconcile:                 # OKF extension; drift binding, if the card is sourced
  direction: code-is-truth
  bindings:
    - doc_anchor: <anchor or whole-doc>
      governs: <a sources entry>
---

Two or three short paragraphs or bullets. State the fact, the enforcement or
evidence, and anything a reader would otherwise get wrong.
```

Order OKF-reserved fields first (`type`, `title`, `description`, `tags`,
`timestamp`), then the extensions.

## OKF (Open Knowledge Format)

These cards follow OKF, the Open Knowledge Format standard published
2026-06-12: markdown plus YAML frontmatter, one fact per card, cross-linked
and git-native. OKF reserves six fields - `type, title, description, resource,
tags, timestamp` - and permits extension fields alongside them. Only `type` is
required.

Field mapping (the contract this document is the authority for):

| Field | OKF status | Notes |
|---|---|---|
| `type` | OKF-REQUIRED | closed vocabulary `{convention, mechanism}` |
| `title` | OKF-reserved | the fact, as a sentence |
| `description` | OKF-reserved | one-line summary |
| `tags` | OKF-reserved | topic list |
| `timestamp` | OKF-reserved | `YYYY-MM-DD`; formerly `updated` |
| `resource` | OKF-reserved | optional, unused (no card has a natural URL yet) |
| `id` | extension | filename without `.md`, kebab-case |
| `related` | extension | other card ids |
| `adr` | extension | backing decision records |
| `confidence` | extension | high / medium / low |
| `sources` | extension | proof-of-claim file globs; NOT `resource` |
| `reconcile` | extension | reconciler drift-binding block (see below) |

Rationale:

- `type` is the only OKF-required field. Its vocabulary is closed to
  `convention` (a discipline the team keeps) and `mechanism` (a
  cooperation-free enforcement). A card that fits neither is a signal to stop
  and decide, not to invent a third value.
- `sources` is deliberately NOT remapped to OKF's `resource`. They differ:
  `resource` is the canonical link to the resource a card describes, while
  `sources` are proof-of-claim file globs the drift reconciler checks against.
- `resource` stays reserved but unused until a card has a natural URL.
- `reconcile:` is declared an official OKF extension field (see below), so one
  frontmatter format serves both this knowledge base and the drift reconciler.

### `reconcile:` is an OKF extension field

The drift reconciler (docs/adr/0003, `scripts/reconcile/`) reads a nested
`reconcile:` block from a doc's frontmatter. That block is an OKF extension
field: a single card can be simultaneously an OKF document (its scalar OKF
fields and extensions) and a reconcile-governed one (the `reconcile:` block).
One frontmatter format covers both; see docs/specs/reconcile.md.

Every sourced card carries a `code-is-truth` `reconcile:` binding whose
`governs` is its `sources`, so each card's claim is drift-checked against the
file that proves it.

## Conventions

- **One fact per card.** A card that needs sections is two cards.
- **confidence: high** means verified against the sources and, where it is a
  decision, ADR-backed. Anything softer is medium or low.
- **sources** point at the code that proves the claim, so staleness is
  checkable.
- When the fact changes, update the card and its `timestamp` date in the same
  PR - a stale card is worse than no card.

## Index

- [shim-files-point-to-agents-md](shim-files-point-to-agents-md.md) - harness rule files are pointers, never content
- [handoffs-are-files](handoffs-are-files.md) - anything worth keeping from a session lives in a committed file
- [gnhf-safe-subcommands](gnhf-safe-subcommands.md) - criterion for green-flagging subcommands of blocked tools in unattended runs
- [knowledge-cards-follow-okf](knowledge-cards-follow-okf.md) - the knowledge corpus conforms to OKF; README is the format authority
