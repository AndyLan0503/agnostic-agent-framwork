---
type: convention
title: Knowledge cards follow OKF (Open Knowledge Format)
description: The knowledge corpus conforms to OKF; framework/knowledge/README.md is the format authority and field-mapping contract.
tags: [okf, knowledge, conventions, source-of-truth]
timestamp: 2026-09-14
id: knowledge-cards-follow-okf
related: [handoffs-are-files, shim-files-point-to-agents-md]
confidence: high
sources: ["framework/knowledge/README.md"]
---

## Fact

The `framework/knowledge/` cards conform to OKF (Open Knowledge Format, published
2026-06-12): markdown plus YAML frontmatter, one fact per card, git-native.
OKF reserves `type, title, description, resource, tags, timestamp` and permits
extension fields; only `type` is required, drawn here from the closed
vocabulary `{convention, mechanism}`.

The format authority - the reserved-vs-extension split, the field-mapping
table, and the card body's single `## Fact` heading - is
`framework/knowledge/README.md`, not an ADR. `sources` is a repo extension, not OKF's
`resource`; `resource` stays reserved but unused.

Drift bindings are not a frontmatter field. They live out-of-band in
`knowform.bindings.json`, which addresses a card by heading path, so a card
carries no tool-specific markup and stays a plain OKF document.
