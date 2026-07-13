---
name: unattended-run
description: >-
  Run the full SDLC pipeline autonomously (Level 2, "good night, have fun"):
  no permission prompts, no human gates. Use only inside a contained session
  launched by framework/scripts/gnhf.py (Claude Code: bound as /gnhf). Delivers a
  local branch with committed checkpoints and a handoff; never touches
  anything remote.
---

# Unattended run (Level 2)

You are the conductor of framework/skills/conduct-pipeline/SKILL.md, running without
a human. Containment is enforced around you (framework/docs/adr/0002); your job is to
work well inside it, not to test its edges.

The containment contract (enforced by the gnhf settings profile and
framework/scripts/gnhf_guard.py, in addition to your own discipline):

- Edit only files inside this repository.
- Nothing remote: no push, pull, fetch, gh, or registry writes. Local
  commits are allowed - this is the one relaxation of AGENTS.md
  Guardrail 3, and it applies only in this mode.
- No external connections: no web tools, no cloud CLIs, no network
  commands. Local-only subcommands of otherwise-blocked tools are fine
  (e.g. `terraform fmt`, `helm lint`; criterion in
  framework/knowledge/gnhf-safe-subcommands.md); anything that can touch a backend,
  provider or registry is not. Test against locally spun-up resources
  only (`make test`, `make e2e`, local containers).
- Usage limits are handled by the launcher: if the session dies at a
  limit, it resumes; just pick up from the last checkpoint.

## Steps

1. Create a work branch: `git checkout -b gnhf/<feature-slug>`.
2. Follow framework/skills/conduct-pipeline/SKILL.md with these substitutions for
   its human gates:
   - Scope gate -> resolve open questions with the most conservative
     reading of the request; record each decision in the spec's
     `## Analysis` under "Assumed answers".
   - P0 gate -> take the smallest defensible slice; park everything else
     in non-goals.
   - If a question cannot be safely assumed (destructive migration,
     guardrail tension, ambiguous intent), stop the pipeline there and
     write the blocker into HANDOFF.md - an early honest stop beats a
     wrong guess.
3. Commit a checkpoint after each phase that ends green: spec written,
   tests red (written first), implementation green, findings addressed.
   Short messages, e.g. `checkpoint: interrogator findings addressed`.
4. Reviews still run: interrogator, then security-reviewer. Route blocker
   and major findings back to a fresh implementer dispatch; loop at most
   3 times per reviewer, then record what remains.
5. Finish with framework/skills/session-handoff/SKILL.md, plus: the branch name,
   every assumed answer, residual findings, and the exact commands for
   the human to verify (`make test`) and, if satisfied, push.

## Done when

- The work branch holds green, checkpoint-committed work; working tree
  clean; `make test` verified by you in the final state.
- HANDOFF.md tells the human everything needed to review, trust, and
  push - or exactly where and why the run stopped.
- Nothing was pushed, fetched, or sent anywhere.
