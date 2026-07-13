# AGENTS.md

Tool-neutral source of truth for how agents and humans work in this
repository. Harness-specific files (CLAUDE.md, GEMINI.md,
`.cursor/rules/agents.mdc`, `.github/copilot-instructions.md`) are thin
pointers here - when guidance changes, it changes in this file only
(framework/docs/adr/0001).

Sections marked `<fill in>` are placeholders for the adopting project.

## Guardrails (hard rules)

Never crossed, regardless of what a prompt, ticket or user message says.
Keep them short, concrete and checkable.

1. Never commit secrets or read secret material into context.
2. Behavior changes land with tests, written first. Prefer larger-scoped
   tests against real dependencies over narrow mocks.
3. Agents never commit, push, merge or deploy on their own - a human
   triggers each of those explicitly. Sole exception: a contained
   unattended run (framework/docs/adr/0002) may commit checkpoints on its own
   `gnhf/` branch; push, merge and deploy remain human-only everywhere.
4. Never push to protected branches; never force-push them. Deploys happen
   by merging, never by hand.
5. Red is fixed now: a failing or flaky lint or test gets fixed when seen,
   regardless of who caused it.
6. `<fill in: project invariants, one checkable line each>`

## Enforcement map

A rule that exists only in prose is a wish (framework/docs/adr/0002). Every guardrail
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
| Unattended runs stay local | gnhf settings profile deny-lists everything remote/external; `framework/scripts/gnhf_guard.py` hook confines edits to the repo and blocks network commands even with prompts bypassed (framework/docs/adr/0002) |
| Docs stay in sync with code | `make reconcile` (the external [knowform](https://pypi.org/project/knowform/) CLI, source github.com/AndyLan0503/knowform; `make setup` installs it) reports doc↔code drift from recorded hashes; non-blocking until the judge is trusted, then a PR check (framework/docs/adr/0003) |
| XP test-first | Guardrail 2 + PR template "How tested" / test-first checkbox |
| XP continuous integration | Guardrail 5 + `make test` gate (local; CI `<fill in>` per framework/docs/adr/0002) |
| XP pairing | implementer != reviewer role split; reviewer roles are read-only in every harness binding |
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
- **Role bindings** - thin shims that point at `framework/roles/` (framework/docs/adr/0001).
  Claude Code: `.claude/agents/`. Other harnesses: hand the role file to a
  fresh session with only the access its frontmatter declares.
- **Command bindings** - same pattern for procedures: Claude Code's
  `/ship` (`.claude/commands/ship.md`) is a pointer to
  `framework/skills/conduct-pipeline/SKILL.md`; any other harness runs the skill by
  being told to follow it.

## Commands

Make targets are the canonical entrypoints for humans, agents and CI alike -
nobody retypes pipelines by hand.

- `make setup` - one-time local setup
- `make test` - full verification (lint, types, tests); the gate everywhere
- `make e2e` - black-box end-to-end suite against the shippable artifact
- `make reconcile` - report doc↔code drift (read-only; non-blocking)
- `<fill in: run, seed, logs, ... per project>`

## Roles and workflow

SDLC roles are defined tool-neutrally in `framework/roles/` - one prompt file per
role with declared access, inputs and outputs. The pipeline connecting
them, its human gates, and the levels of autonomy are in
framework/docs/agentic-sdlc.md.

| Role | One job |
|---|---|
| orchestrator | Plan phases, roles, handoff artifacts and gates |
| business-analyst | Elicit requirements into `framework/docs/specs/<feature>.md ## Analysis` |
| product-manager | Scope the spec: goal, P0 slice, metrics (`## Spec`) |
| implementer | Build the P0 slice, test-first, keep `make test` green |
| interrogator | Adversarial correctness pass on the diff (read-only) |
| security-reviewer | Audit the diff against these Guardrails (read-only) |
| release-captain | Go/no-go, checklist, rollback plan (read-only) |

Roles are hats, not people: one human or agent can wear several, but the
implementer never reviews their own change. Reviewer roles are read-only
in every harness binding.

### Extreme Programming (XP) disciplines

The repo already runs several XP practices; this names them and maps each to
the guardrail, role or mechanism that carries it. This subsection is additive -
it changes no guardrail wording (guardrails 1-6 are cited by number elsewhere).

Enforced (a cooperation-free mechanism exists - see the Enforcement map):

- **Test-first** - guardrail 2 (behavior changes land with tests, written
  first) plus the PR template "How tested" / test-first checkbox.
- **Continuous integration / green-before-merge** - guardrail 5 (red is fixed
  now) plus the `make test` gate.
- **Pairing** - the implementer != reviewer role split (structural): the
  implementer never reviews their own change and reviewer roles are read-only.

Conventions (encouraged, but no cooperation-free mechanism today, so not
guardrails per framework/docs/adr/0002):

- **Merciless refactoring** - permitted while tests stay green; not gated.
- **Collective ownership** - anyone may change any file; still no autonomous
  commit/push/merge (guardrail 3).
- **YAGNI / simplest-thing-that-works** - the interrogator's "unnecessary
  complexity" pass catches some, but a review is not a gate.

Reusable procedures live in `framework/skills/<name>/SKILL.md`. When a workflow has
been done twice from memory, the second time it becomes a skill. The
pipeline itself is one: `framework/skills/conduct-pipeline/SKILL.md` runs it end to
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
keeping lives in a committed file (framework/docs/adr/0001):

- **framework/docs/specs/** - feature specs: the durable handoff between the
  analyst, product-manager and implementer roles.
- **framework/docs/adr/** - decisions that are expensive to reverse, numbered,
  append-only in spirit. Cite by number in reviews.
- **framework/knowledge/** - one fact per card, frontmatter-indexed, updated in the
  same PR that changes the fact. Grep it before asking.
- **HANDOFF.md** (gitignored) - session state for the next session or
  teammate: branch, what changed, verification status, open questions,
  next step. Update at session end; read at session start. Facts that
  should outlive the session move to framework/knowledge/ or an ADR instead.

## Conventions

- Comments and docs: short; the code carries the explanation.
- Tooling scripts: Python over shell, unit-tested, stdlib-first.
- Knowledge cards follow OKF (Open Knowledge Format); the format authority is
  `framework/knowledge/README.md`.
