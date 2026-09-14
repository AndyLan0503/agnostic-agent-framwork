---
type: convention
title: A check that does not report what it examined can pass while examining nothing
description: The dominant defect class in agent-written enforcement code - a green gate whose scan set is empty for the wrong reason.
tags: [enforcement, testing, agents, ci]
timestamp: 2026-09-14
id: checks-report-what-they-examined
related: [gnhf-safe-subcommands]
confidence: high
sources: ["framework/roles/implementer.md", "framework/scripts/test_framework_contract.py"]
---

## Fact

In a single adoption, four separate checks passed while examining nothing.
Each was carefully written, each had been run, each was green:

| Check | Passed while |
|---|---|
| Android manifest permission | keyed to the literal path `apps/mobile`; any other app directory name scanned nothing, forever |
| ESLint network ban | scoped to `**/*.ts`, so it skipped `.tsx` - the extension the UI is written in |
| Secret scanner and manifest checker | the ignored-directory list matched the **absolute** path, so a checkout under any folder named `build` scanned nothing |
| Python version gate | accepted anything executable, so `PYTHON=/usr/bin/true make test` ran zero tests and reported green |

Three of the four had tests, and the tests passed, because each exercised the
one input that already worked: a fixture at `apps/mobile`, a `.ts` file, a
checkout outside `build`. A check's scan set is an input like any other, and
the empty scan set is the input nobody writes a fixture for. A gate reports
two different things with the same exit code - "I looked and found nothing
wrong" and "I did not look" - and only the first one is worth anything.

So: **every check reports what it examined** - a count of files, packages or
rows - **and ships a test that fails when that count is zero for the wrong
reason.** A gate that prints `214 packages screened` cannot silently become a
gate that screens none. `framework/roles/implementer.md` carries this as a
numbered obligation; `test_table_parses` in
`framework/scripts/test_framework_contract.py` is the in-repo example, refusing
to judge the enforcement map at all until it has parsed at least `MIN_ROWS`
rows out of it.

Zero is sometimes the right answer - a rule with no violations today, an
adopter who has filled in every row. The obligation is not "assert non-zero",
it is "make the difference visible and test the wrong-reason case".
