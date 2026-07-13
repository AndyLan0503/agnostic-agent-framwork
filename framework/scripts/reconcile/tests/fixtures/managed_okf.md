---
type: mechanism
title: A full OKF-conformant card that is also reconcile-governed
description: Exercises OKF scalars coexisting with a reconcile block in one frontmatter.
tags: [okf, reconcile]
timestamp: 2026-07-13
id: managed-okf
related: [managed-add]
adr: ["0003"]
confidence: high
sources: ["calc.py"]
reconcile:
  direction: code-is-truth
  bindings:
    - doc_anchor: okf-behavior
      governs: calc.py
      code_anchor: "def add"
---

# OKF + reconcile

<!-- reconcile:okf-behavior:start -->
`add(a, b)` returns the sum, and this card is a full OKF document too.
<!-- reconcile:okf-behavior:end -->
