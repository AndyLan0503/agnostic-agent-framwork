# Contributing

Guardrails, git/GitHub behavior and the enforcement map live in
[AGENTS.md](AGENTS.md) - read it first. This file covers mechanics.

## First-time setup

```
make setup
```

## Day to day

- `make test` before every commit - CI in the adopting project re-runs the
  same gate on every PR.
- Work test-first. A behavior change without a test does not merge.
- Branch from the integration branch; open a PR and fill the checklist
  honestly. One gitmoji per PR.
- Ending a session or handing work to a teammate? Follow
  `skills/session-handoff/SKILL.md` to update the gitignored `HANDOFF.md`
  so the next person starts warm.
- Feature work follows the pipeline in `docs/agentic-sdlc.md`; role
  prompts live in `roles/` and run from any harness.

## Where things go

- A decision that is expensive to reverse -> `docs/adr/`
- A fact worth remembering -> a card in `knowledge/`
- A procedure done twice -> a runbook in `skills/`
- Requirements and scope for a feature -> `docs/specs/<feature>.md`
- A rule agents must follow -> `AGENTS.md`, wired into the enforcement map
