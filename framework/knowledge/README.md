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
---

## Fact

Two or three short paragraphs or bullets. State the fact, the enforcement or
evidence, and anything a reader would otherwise get wrong.
```

Order OKF-reserved fields first (`type`, `title`, `description`, `tags`,
`timestamp`), then the extensions.

The body opens with a single `## Fact` heading and carries no others. It is
what the drift reconciler addresses the card by (see below), and it is the
reason "one fact per card" is a format rule and not only advice: a card with
several sections has no single region a binding can point at.

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

Rationale:

- `type` is the only OKF-required field. Its vocabulary is closed to
  `convention` (a discipline the team keeps) and `mechanism` (a
  cooperation-free enforcement). A card that fits neither is a signal to stop
  and decide, not to invent a third value.
- `sources` is deliberately NOT remapped to OKF's `resource`. They differ:
  `resource` is the canonical link to the resource a card describes, while
  `sources` are proof-of-claim file globs the drift reconciler checks against.
- `resource` stays reserved but unused until a card has a natural URL.
- Drift bindings are deliberately NOT a frontmatter field. They live
  out-of-band in `knowform.bindings.json` (see below), so a card stays a plain
  OKF document with no tool-specific markup in it.

### Drift bindings live in `knowform.bindings.json`

The drift reconciler is knowform, an external published tool
(https://pypi.org/project/knowform/, github.com/AndyLan0503/knowform). Bindings
are declared out-of-band in `knowform.bindings.json` at the repo root, and a
card carries no knowform markup at all - the cards stay plain OKF documents.

A binding addresses a card region by heading path, optionally narrowed to one
blank-line-separated block under it:

```json
{"doc": "framework/knowledge/<card>.md", "heading": ["Fact"],
 "governs": "<a sources entry>", "direction": "code-is-truth"}
```

Add `"block": N` to bind a single paragraph or list rather than the whole card
- `N` counts blocks under the heading, so a binding narrowed this way moves
when the card is re-ordered and the next `make reconcile` reports it.

Every sourced card is `code-is-truth`-bound once per `sources` entry, so each
card's claim is drift-checked against the file that proves it.
`framework/scripts/test_knowledge_cards.py` asserts that correspondence in both
directions; `knowform.lock` records the blessed hashes and is regenerated with
`knowform sync`.

knowform is pinned in `make setup` to `>=0.3,<0.4`. The pin is load-bearing:
0.3.0 removed the older inline-frontmatter binding model, and an unpinned
install silently upgraded into a version that read zero bindings and reported
success.

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
- [checks-report-what-they-examined](checks-report-what-they-examined.md) - a check that does not report its scan set can pass while examining nothing
