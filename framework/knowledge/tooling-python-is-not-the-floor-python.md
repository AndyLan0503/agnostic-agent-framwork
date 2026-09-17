---
type: mechanism
title: knowform runs from .venv-tools on Python 3.10+, never on the 3.9 floor
description: The floor interpreter runs the suites; a tool needing a newer Python gets its own venv rather than raising the floor.
tags: [python, tooling, knowform, setup]
timestamp: 2026-09-17
id: tooling-python-is-not-the-floor-python
related: [knowledge-cards-follow-okf]
adr: ["0003"]
confidence: high
sources: ["Makefile"]
---

## Fact

Two Python versions are in play and conflating them breaks `make setup`. The
floor is 3.9.6, the stock macOS interpreter: it runs every suite, and nothing
needs installing to use it. knowform requires 3.10 or newer. `make setup`
shipped as `pip install "knowform>=0.3,<0.4"`, which on a stock macOS box fails
twice over - bare `pip` is not on PATH, and the 3.9 interpreter behind `pip3`
is below knowform's floor, so pip reports no matching distribution.

`make setup` now resolves `TOOLS_PYTHON` from `python3.13` down to
`python3.10`, builds `.venv-tools` with it, and installs knowform there;
`make reconcile` calls `.venv-tools/bin/knowform` by path rather than whatever
PATH resolves. Where the search misses, pass it:
`make setup TOOLS_PYTHON=/path/to/python3.12`.

The rule generalises: a tool that needs a newer Python gets its own
interpreter, never a raised floor, because the floor is what lets a fresh
checkout run `make test` before installing anything.
`test_setup_does_not_install_knowform_with_the_floor_interpreter` fails a
recipe that reaches for `pip` or `python3 -m pip` again, and its sibling fails
a `reconcile` that calls a knowform other than the one `setup` installed.
