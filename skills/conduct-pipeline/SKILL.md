---
name: conduct-pipeline
description: >-
  Conduct the full SDLC pipeline for a feature request at autonomy Level 1:
  dispatch each role from roles/, thread artifacts between them, pause at
  every human gate. Use when a feature should go from request to
  PR-ready without the human driving each role by hand. Claude Code binds
  this as /ship.
---

# Conduct the pipeline (Level 1)

You are the conductor: a main agent session that dispatches roles and owns
the gates. The pipeline and its rationale are in docs/agentic-sdlc.md.

Invariants to preserve:
- Roles start cold: each dispatch is a fresh subagent or session given the
  role file (`roles/<name>.md`), the artifact paths, and a request summary.
- Reviewer roles run with read-only access.
- Never commit, push, merge or deploy - the human does that after the
  final gate.
- Verification is yours: re-run `make test` after implementation; never
  accept a role's claim of green.

## Steps

1. Prune the pipeline to the change size (a small fix skips analyst/PM;
   when unsure, dispatch the orchestrator role first and follow its plan).
2. Dispatch **business-analyst** -> `docs/specs/<feature-slug>.md`
   `## Analysis`.
   GATE: present scope and open questions to the human; wait for answers.
3. Dispatch **product-manager** with the spec path -> `## Spec` appended.
   GATE: present the P0 slice; wait for confirmation.
4. Dispatch **implementer(s)** with the spec path. Then run `make test`
   yourself and confirm green.
5. Dispatch **interrogator** on the diff (read-only). Route blocker and
   major findings back to a fresh implementer dispatch, quoting the
   finding text; repeat until clean or the human accepts the residue.
6. Dispatch **security-reviewer** on the diff (read-only); same routing
   rule.
7. Summarize: what was built, test evidence, residual findings, spec path.
   GATE: stop. The human commits, pushes and opens the PR
   (release-captain role can pre-flight it).

## Done when

- `make test` green, verified by the conductor.
- Blocker and major findings resolved or explicitly accepted by the human.
- Spec file reflects what was actually built.
- Nothing committed, pushed or deployed.
