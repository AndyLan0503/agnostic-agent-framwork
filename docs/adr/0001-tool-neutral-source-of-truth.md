# ADR-0001: Everything durable lives in tool-neutral files; harness bindings are thin shims

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** framework authors

## Context

Three pressures push in the same direction. Every harness wants its own
rule file (CLAUDE.md, GEMINI.md, `.cursor/rules/`, Copilot instructions),
and duplicated guidance drifts immediately. Agent sessions hold decisions,
facts and work-in-flight in chat history, which evaporates at session end
and is invisible to teammates on other harnesses. And role prompts or
procedures defined in one harness's format lock the team's most valuable
prompt assets to a single tool.

## Decision

All durable content lives in tool-neutral committed files, each kind in
one canonical place:

- Guidance and guardrails: `AGENTS.md`.
- Decisions: `docs/adr/`. Facts: `knowledge/` cards, updated in the same
  PR that changes the fact. Feature handoffs: `docs/specs/<feature>.md`
  and the git diff. Session state: gitignored `HANDOFF.md`.
- Role prompts: `roles/` (frontmatter: name, description, access, inputs,
  outputs). Procedures: `skills/<name>/SKILL.md`.

Every harness integration is a thin shim that adds nothing: pointer rule
files, `.claude/agents/` bindings that say "read `roles/<name>.md`",
commands that say "follow `skills/<name>/SKILL.md`". Roles hand off
through the committed artifacts, and are handed artifact paths explicitly
because they start cold.

## Alternatives considered

- **Per-harness definitions** - drifts; improvements made in one tool
  never reach teammates on another.
- **Harness memory features** - ties state to one tool and one user,
  hidden from code review.
- **Generating bindings from neutral sources** - solves drift but adds
  build machinery for what a three-line shim does for free.

## Consequences

A rule, role or fact changes in exactly one reviewed place and reaches
every harness. Any teammate or agent joins mid-stream by reading files;
work is auditable because the artifact proves what was done. Costs: one
indirection when a shim loads, and discipline - if it only exists in the
conversation, it does not exist for the team. Content in a shim beyond
the pointer is a bug.
