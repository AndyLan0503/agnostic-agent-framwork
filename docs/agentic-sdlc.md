# The agentic SDLC

How a change moves from request to merge, in any harness. Role definitions
live in `roles/`; this document is the pipeline that connects them.

## Two facts that shape everything

1. **Roles start cold.** A role invocation (subagent, fresh session, or a
   teammate's harness) cannot see prior conversation. Handoffs therefore go
   through durable artifacts - the spec file, the git diff, ADRs, knowledge
   cards - and every role is handed artifact paths explicitly
   (docs/adr/0001).
2. **Gates are mechanical.** Commit, push, merge and deploy are human
   actions by construction: those commands are absent from every harness's
   allowlist (docs/adr/0002). An agent finishing a phase stops and reports;
   it cannot proceed past a gate even if convinced it should.

An agent cannot claim it did something; the artifact proves what was done.

## The pipeline

Prune to fit the change - a one-line bugfix does not need an analyst.

```
request
  -> orchestrator        plan phases, roles, artifacts, gates
  -> business-analyst    requirements + acceptance criteria   -> docs/specs/<feature>.md  ## Analysis
        GATE: human confirms scope and answers open questions
  -> product-manager     scoped spec, P0 slice, metrics       -> same file, ## Spec
        GATE: human confirms the P0 slice
  -> implementer(s)      test-first implementation            -> code + tests, make test green
  -> interrogator        adversarial correctness pass         -> findings by severity
  -> security-reviewer   guardrail / invariant audit          -> findings
        (blocker/major findings route back to a fresh implementer)
  -> release-captain     go/no-go + rollback plan
        GATE: human commits, pushes, opens the PR, merges
```

Whoever drives the pipeline re-runs `make test` after implementation rather
than trusting the implementer's report - the judge is a mechanism.

## Levels of autonomy

| Level | Who drives | Pauses | Use for |
|---|---|---|---|
| 0 - manual | A human invokes each role, in any harness | between every role | learning, high-stakes work |
| 1 - conducted | One main agent session dispatches roles and threads artifacts, per `skills/conduct-pipeline/SKILL.md` (Claude Code binding: `/ship`) | at every human gate | real feature work (default) |
| 2 - headless | `scripts/gnhf.py` launches a contained session running `skills/unattended-run/SKILL.md` (Claude Code binding: `/gnhf`) | none; assumptions recorded, checkpoints committed locally on a `gnhf/` branch, never pushes | overnight runs, after Level 1 is trusted |

Level 2 trades gates for containment: prompts are bypassed, but a settings
profile plus a PreToolUse guard confine the run to local edits, local
commits and local testing, and the launcher sleeps through usage-limit
windows and resumes (docs/adr/0002). Use it only after Level 1 is trusted
in the adopting project.

Practical usage of both levels - invocation, gates, steering, the morning
review ritual - is in docs/running-the-pipeline.md.

## Separation of powers

Roles are hats - one human or agent can wear several, but never implementer
and reviewer on the same change. Reviewer roles (`interrogator`,
`security-reviewer`, `release-captain`) declare `access: read-only` and are
bound with no write permission in every harness, so the separation is
enforced, not requested.
