---
id: gnhf-safe-subcommands
title: The gnhf guard allows local-only subcommands of blocked tools
tags: [gnhf, containment, agents, security]
related: [handoffs-are-files]
adr: ["0002"]
confidence: high
sources: ["scripts/gnhf_guard.py", "scripts/test_gnhf_guard.py"]
updated: 2026-07-03
---

The unattended-run guard blocks tool families (`terraform`, `helm`, remote
git, ...) but whitelists specific subcommands in `SAFE_BASH`
(scripts/gnhf_guard.py). Criterion for adding one - all four must hold:

1. No network connection under any usage.
2. No remote mutation.
3. No secret reads.
4. No flag can introduce a remote source (`helm template --repo`,
   `terraform plan`'s backend access - excluded for exactly this).

A safe pattern must match the entire command, so chaining or substitution
(`terraform fmt && curl ...`) never rides through. Add new entries with a
test in `test_gnhf_guard.py` first.
