# Contributing

Guardrails, git/GitHub behavior and the enforcement map live in
[AGENTS.md](AGENTS.md) - read it first. This file covers mechanics.

## First-time setup

```
make setup
```

`make setup` needs a Python >= 3.10 on PATH (`python3.10` through
`python3.13`, or `make setup TOOLS_PYTHON=/path/to/python3.12`). That is for
knowform only: it goes into `.venv-tools`, and the test suites keep running on
the stock 3.9 interpreter, which needs nothing installed.

`make setup` installs from PyPI, so it is deliberately absent from the
auto-approved command list: an agent that reaches it stops and asks. Every
other Make target (`help`, `test`, `e2e`, `reconcile`) is allowed by name.
Bare `make` runs `help`.

## Day to day

- `make test` before every commit - CI in the adopting project re-runs the
  same gate on every PR.
- Adding a gate of any kind? It reports what it examined and ships a test for
  the zero-scan case - `framework/knowledge/checks-report-what-they-examined.md`.
- After a review, `git status`. Reviewer roles are read-only by instruction,
  not by harness enforcement, and anything a reviewer wrote is an unreviewed
  diff (AGENTS.md "Reviewer access").
- Work test-first. A behavior change without a test does not merge.
- Branch from the integration branch; open a PR and fill the checklist
  honestly. One gitmoji per PR.
- Ending a session or handing work to a teammate? Follow
  `framework/skills/session-handoff/SKILL.md` to update the gitignored `HANDOFF.md`
  so the next person starts warm.
- Feature work follows the pipeline in `framework/docs/agentic-sdlc.md`; role
  prompts live in `framework/roles/` and run from any harness.

## Where things go

- A decision that is expensive to reverse -> `framework/docs/adr/`
- A fact worth remembering -> a card in `framework/knowledge/`
- A procedure done twice -> a runbook in `framework/skills/`
- Requirements and scope for a feature -> `framework/docs/specs/<feature>.md`
- A rule agents must follow -> `AGENTS.md`, wired into the enforcement map

## Adding an enforcement-map row

`framework/scripts/test_framework_contract.py` holds the enforcement map to the
standard it states. Every row's Mechanism cell must contain at least one of:

- a repository path that exists (`framework/scripts/gnhf_guard.py`),
- a `make <target>` the Makefile defines,
- or a dated deferral, exactly `<fill in by YYYY-MM-DD: what will back this
  rule>` - the date is when the row must be honoured by.

A row stating a limit and backing it with prose alone fails the suite. Paths
and `make` targets a row cites are checked for existence, so a row cannot name
a script that was renamed or never written.

A fourth shape exists for limits only the adopting project can defend - the
project invariants, a secret scanner: mark the cell `Adopter-owned` and cite
the adoption step that fills it in. The suite requires such a row to name
`framework/skills/adopt-framework/SKILL.md`, so the marker cannot be used as a
polite way of saying nothing.

### Deferral dates expire here, and only here

The suite fails on a deferral whose date has passed - in *this* repository. In
a repository that adopted the scaffold, the same check skips.

The reasoning is that a deadline is only a mechanism where somebody can act on
it. A date shipped in the scaffold and copied into fifty repositories would
turn red in all fifty on a day nobody there chose, and a check that goes red
for reasons the team cannot fix is a check the team switches off. So the date
is enforced where it was chosen and inert where it was inherited.

`is_framework_repo()` in `framework/scripts/test_framework_contract.py` tells
the two apart: the framework checkout ships `framework/scripts/adopt.py`
(which `adopt.py` excludes from everything it copies) and carries no
`.framework-version`; every adopted copy carries one. Both conditions must
hold, so a project that vendored `adopt.py` by hand still reads as adopted.

**If you adopted the scaffold:** replace the inherited dates with dates your
team chose during adoption (step 7). The check does not run for you until you
do, and a date nobody owns is exactly the wish this table forbids.

The scaffold also runs on Python 3.9.6, the stock macOS interpreter: scripts
under `framework/scripts/` are parsed at that language level, and PEP 604
`X | Y` annotations need `from __future__ import annotations`.
