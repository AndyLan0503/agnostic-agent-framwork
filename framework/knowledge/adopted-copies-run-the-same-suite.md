---
type: mechanism
title: Every test here runs twice, once as the framework and once as an adopted copy
description: test_adoption_smoke builds a synthetic adopted repository from the working tree and runs the whole suite inside it.
tags: [adoption, testing, enforcement, e2e]
timestamp: 2026-09-17
id: adopted-copies-run-the-same-suite
related: [checks-report-what-they-examined]
confidence: high
---

## Fact

Every module under `framework/scripts/` is copied verbatim into every adopting
repository, so each test runs in two places whose truths differ: here, where
the checkout *is* the framework, and there, where it is not. A test asserting a
framework-only fact passes here and fails in every adopted repo on that repo's
first `make test` - which is precisely what shipped in 201dc4f, where
`test_this_checkout_is_the_framework_repository` asserted its own premise
unguarded.

`framework/scripts/test_adoption_smoke.py` closes that gap with the real thing
rather than a proxy: it copies the working tree through `adopt.ships` - the
same exclusion rules the installer uses - stamps a `.framework-version`, makes
it a git repository, and runs the entire suite inside it as a subprocess. It
reports the file count and the test count, so a run that copied nothing cannot
read as a pass. It builds from the **working tree**, not `HEAD`, because
`adopt.scaffold_files` reads HEAD and would test the previous commit - which
would deadlock the fix for exactly this bug class behind its own gate.

The same reasoning bans a whole class of reference: **a document that ships
may only cite paths that ship.** AGENTS.md, its enforcement map, every
knowledge card and `knowform.bindings.json` are all copied verbatim, so a row,
a `sources` entry or a binding naming a framework-only file resolves to nothing
in every adopted repository - a red suite there, and a reconciler pointed at a
file that is not present. That is why this card carries no `sources` despite
having an obvious proof file, and why no enforcement-map row cites
`test_adoption_smoke.py`. `test_every_drift_binding_ships` holds the line for
bindings; the smoke run below catches the rest.

The module is in `adopt.EXCLUDED_FILES` and asserts that it is: shipped, it
would build an adopted copy inside every adopted copy and import an `adopt.py`
that adoption does not install. When a framework-only assertion is genuinely
needed, guard it on `.framework-version` the way
`test_no_deferral_in_this_repository_has_expired` does.
