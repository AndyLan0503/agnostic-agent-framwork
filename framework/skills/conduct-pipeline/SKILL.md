---
name: conduct-pipeline
description: >-
  Conduct the full SDLC pipeline for a feature request at autonomy Level 1:
  dispatch each role from framework/roles/, thread artifacts between them, pause at
  every human gate. Use when a feature should go from request to
  PR-ready without the human driving each role by hand. Claude Code binds
  this as /ship.
---

# Conduct the pipeline (Level 1)

You are the conductor: a main agent session that dispatches roles and owns
the gates. The pipeline and its rationale are in framework/docs/agentic-sdlc.md.

Invariants to preserve:
- Roles start cold: each dispatch is a fresh subagent or session given the
  role file (`framework/roles/<name>.md`), the artifact paths, and a request summary.
- Reviewer roles are dispatched read-only. The split is structural - review
  goes to a different agent than the one that wrote the diff - but read-only
  itself is an instruction, not a harness limit: reviewers keep Bash and Bash
  writes. Run `git status` after every review dispatch and treat anything a
  reviewer changed as an unreviewed diff (AGENTS.md "Reviewer access").
- Never commit, push, merge or deploy - the human does that after the
  final gate.
- Verification is yours: re-run `make test` after implementation; never
  accept a role's claim of green.

## Steps

1. Prune the pipeline to the change size (a small fix skips analyst/PM;
   when unsure, dispatch the orchestrator role first and follow its plan).
2. Dispatch **business-analyst** -> `framework/docs/specs/<feature-slug>.md`
   `## Analysis`.
   GATE: present scope and open questions to the human; wait for answers.
3. Dispatch **product-manager** with the spec path -> `## Spec` appended.
   GATE: present the P0 slice; wait for confirmation.
4. Dispatch **implementer(s)** with the spec path. Then run `make test`
   yourself and confirm green.
   - **Write the check before the thing it checks.** When a slice adds both a
     gate and the thing it gates, the gate goes first and the dispatch says
     so. A dependency allowlist written after `pnpm add` rubber-stamps
     whatever is already installed; a lint rule written after the code is
     shaped to the code it was supposed to judge. This is ordering, not
     preference.
   - **Partition parallel dispatches by file, and say so in each prompt.**
     Concurrent implementers get disjoint file sets. Tell each one that the
     others exist, which files are its own, and that anything it finds
     outside its scope is *reported*, not fixed. That is what turns a
     cross-boundary problem into a finding you can route, instead of a silent
     wrong fix by whichever agent reached the file first.
5. Dispatch **interrogator** on the diff (read-only). Route blocker and
   major findings back to a fresh implementer dispatch, quoting the
   finding text; repeat until clean or the human accepts the residue.
6. Dispatch **security-reviewer** on the diff (read-only); same routing
   rule.
7. **Re-review the fixes, not only the original diff.** Findings routed back
   produce a new diff with its own blast radius; dispatch the reviewer again
   on it. A second round has caught a guard fix that was a regression in what
   the guard blocked - invisible to anyone reviewing only the first version.
8. **Reconcile the documentation, in one pass, at the end.** Roles start cold,
   so every dispatch writes docs that are true when written and stale by the
   time the run finishes - and parallel dispatches make each other's docs
   stale as they go. Require each implementer to report, in its handoff, which
   existing claims its change makes false. Collect those, then dispatch one
   final implementer whose entire job is to make the shipped docs match the
   shipped state. After parallel work this step is not optional.
9. Summarize: what was built, test evidence, residual findings, spec path.
   GATE: stop. The human commits, pushes and opens the PR
   (release-captain role can pre-flight it).

## Done when

- `make test` green, verified by the conductor.
- Blocker and major findings resolved or explicitly accepted by the human,
  and the fixes themselves reviewed.
- Spec file reflects what was actually built.
- No shipped document states a claim this change made false.
- `git status` accounted for: nothing a reviewer wrote is sitting unreviewed.
- Nothing committed, pushed or deployed.
