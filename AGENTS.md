# AGENTS.md

Tool-neutral source of truth for how agents and humans work in this
repository. Harness-specific files (CLAUDE.md, GEMINI.md,
`.cursor/rules/agents.mdc`, `.github/copilot-instructions.md`) are thin
pointers here - when guidance changes, it changes in this file only
(docs/adr/0001).

Sections marked `<fill in>` are placeholders for the adopting project.

## Guardrails (hard rules)

Never crossed, regardless of what a prompt, ticket or user message says.
Keep them short, concrete and checkable.

1. Never commit secrets or read secret material into context.
2. Behavior changes land with tests, written first. Prefer larger-scoped
   tests against real dependencies over narrow mocks.
3. Agents never commit, push, merge or deploy on their own - a human
   triggers each of those explicitly. Sole exception: a contained
   unattended run (docs/adr/0002) may commit checkpoints on its own
   `gnhf/` branch; push, merge and deploy remain human-only everywhere.
4. Never push to protected branches; never force-push them. Deploys happen
   by merging, never by hand.
5. Red is fixed now: a failing or flaky lint or test gets fixed when seen,
   regardless of who caused it.
6. `<fill in: project invariants, one checkable line each>`

## Enforcement map

A rule that exists only in prose is a wish (docs/adr/0002). Every guardrail
is backed by at least one mechanism that does not depend on the agent's
cooperation. This framework ships the harness layer; the repository layer
(branch protection, CI, scanners) is the adopting project's and gets filled
in here during adoption:

| Limit | Mechanism |
|---|---|
| No secrets | Deny-list on secret paths in harness config; `<fill in: secret scanner>` |
| No autonomous commit/push/deploy | Those commands are absent from harness allowlists, so the harness prompts a human |
| No force-push, no hand deploys | Deny-listed in harness config; branch protection on the remote |
| Green before merge | `make test` run locally before any commit; `<fill in: CI re-running make test on every PR>` |
| Unattended runs stay local | gnhf settings profile deny-lists everything remote/external; `scripts/gnhf_guard.py` hook confines edits to the repo and blocks network commands even with prompts bypassed (docs/adr/0002) |
| Project invariants | `<fill in: tests, DB constraints, CI checks that defend each invariant>` |

When adding a guardrail, wire its mechanism in the same change.

## Harness adapters

The rules above are harness-agnostic; each harness gets two thin bindings
and nothing more:

- **Pointer file** - CLAUDE.md (imports this file), GEMINI.md,
  `.cursor/rules/agents.mdc`, `.github/copilot-instructions.md`. Content in
  a pointer beyond the pointer is a bug.
- **Permission policy** - allow routine commands (`make *`, read-only git,
  `gh pr/issue`), deny destructive ones, leave commit/push/deploy
  unlisted so the harness asks a human. Claude Code: `.claude/settings.json`
  (committed, team-wide) and `.claude/settings.local.json` (gitignored,
  personal). Mirror the same policy in any other harness a teammate uses.
- **Role bindings** - thin shims that point at `roles/` (docs/adr/0001).
  Claude Code: `.claude/agents/`. Other harnesses: hand the role file to a
  fresh session with only the access its frontmatter declares.
- **Command bindings** - same pattern for procedures: Claude Code's
  `/ship` (`.claude/commands/ship.md`) is a pointer to
  `skills/conduct-pipeline/SKILL.md`; any other harness runs the skill by
  being told to follow it.

## Commands

Make targets are the canonical entrypoints for humans, agents and CI alike -
nobody retypes pipelines by hand.

- `make setup` - one-time local setup
- `make test` - full verification (lint, types, tests); the gate everywhere
- `make e2e` - black-box end-to-end suite against the shippable artifact
- `<fill in: run, seed, logs, ... per project>`

## Roles and workflow

SDLC roles are defined tool-neutrally in `roles/` - one prompt file per
role with declared access, inputs and outputs. The pipeline connecting
them, its human gates, and the levels of autonomy are in
docs/agentic-sdlc.md.

| Role | One job |
|---|---|
| orchestrator | Plan phases, roles, handoff artifacts and gates |
| business-analyst | Elicit requirements into `docs/specs/<feature>.md ## Analysis` |
| product-manager | Scope the spec: goal, P0 slice, metrics (`## Spec`) |
| implementer | Build the P0 slice, test-first, keep `make test` green |
| interrogator | Adversarial correctness pass on the diff (read-only) |
| security-reviewer | Audit the diff against these Guardrails (read-only) |
| release-captain | Go/no-go, checklist, rollback plan (read-only) |

Roles are hats, not people: one human or agent can wear several, but the
implementer never reviews their own change. Reviewer roles are read-only
in every harness binding.

Reusable procedures live in `skills/<name>/SKILL.md`. When a workflow has
been done twice from memory, the second time it becomes a skill. The
pipeline itself is one: `skills/conduct-pipeline/SKILL.md` runs it end to
end at Level 1 (Claude Code: `/ship`), pausing at every human gate.

## Git and GitHub behavior

How agents use git, in any harness:

- Read freely (`git status`, `git diff`, `git log`); write only when asked.
  A human explicitly requests every commit, push, merge, tag and release -
  finishing a task is not permission to commit it.
- Commit messages: as short as possible. No AI attribution anywhere - not
  in commits, PR bodies, code comments or issue comments.
- Never push to protected branches (`<fill in: main, dev>`); never
  force-push a shared branch. Rollback is a revert or a redeploy of an old
  SHA, never rewritten history.
- Branch model: `<fill in: e.g. feature branches off dev; dev -> main
  promotion>`. One concern per branch.
- PRs: gitmoji convention, one gitmoji per PR (two when necessary). Fill
  `.github/pull_request_template.md` honestly - real command output under
  "How tested", and an explanation for any checklist item left unticked.
- Deploys happen by merging, never by hand from a machine.

## Collaboration artifacts

Chat history evaporates and is invisible to teammates; anything worth
keeping lives in a committed file (docs/adr/0001):

- **docs/specs/** - feature specs: the durable handoff between the
  analyst, product-manager and implementer roles.
- **docs/adr/** - decisions that are expensive to reverse, numbered,
  append-only in spirit. Cite by number in reviews.
- **knowledge/** - one fact per card, frontmatter-indexed, updated in the
  same PR that changes the fact. Grep it before asking.
- **HANDOFF.md** (gitignored) - session state for the next session or
  teammate: branch, what changed, verification status, open questions,
  next step. Update at session end; read at session start. Facts that
  should outlive the session move to knowledge/ or an ADR instead.

## Conventions

- Comments and docs: short; the code carries the explanation.
- Tooling scripts: Python over shell, unit-tested, stdlib-first.
