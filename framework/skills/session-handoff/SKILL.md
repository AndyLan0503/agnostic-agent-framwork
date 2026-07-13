---
name: session-handoff
description: >-
  Update HANDOFF.md at the end of a working session (or before handing work
  to a teammate) so the next session starts warm. Use whenever stopping
  mid-task, switching drivers, or ending the day with work in flight.
---

# Session handoff

Invariants to preserve:
- HANDOFF.md is gitignored working state, not documentation. Facts that
  should outlive the session go to framework/knowledge/ or AGENTS.md; decisions go
  to framework/docs/adr/.
- Verification status is reported honestly - "tests not run" is a valid
  entry; a false "green" is not.

## Steps

1. Check state: current branch, `git status`, last few commits.
2. Overwrite (do not append to) `HANDOFF.md` at the repo root with:
   - Date and branch.
   - What changed this session - shipped, in progress, abandoned (and why).
   - Verification status - last `make test` / `make e2e` result.
   - Open questions - decisions waiting on a human.
   - Next steps - the first thing the next session should do.
3. Sweep for durable facts: anything learned this session that belongs in
   AGENTS.md, a knowledge card, or an ADR gets written there now (or
   listed under next steps if it needs discussion).
4. Keep the whole file under a page.

## Done when

- HANDOFF.md reflects only the current state, under a page.
- No durable fact lives only in HANDOFF.md or the chat.
