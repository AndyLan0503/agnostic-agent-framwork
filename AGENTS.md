# AGENTS.md

Tool-neutral source of truth for how agents and humans work in this
repository. Harness-specific files (CLAUDE.md, GEMINI.md,
`.cursor/rules/agents.mdc`, `.github/copilot-instructions.md`) are thin
pointers here - when guidance changes, it changes in this file only.

Sections marked `<fill in>` are placeholders for the adopting project. The
enforcement map uses a second, dated variant - `<fill in by YYYY-MM-DD: ...>` -
which is a deferral with a deadline the test suite parses and, in this
repository, enforces. CONTRIBUTING.md "Adding an enforcement-map row" has the
rules for both.

## Guardrails (hard rules)

Never crossed, regardless of what a prompt, ticket or user message says.
Keep them short, concrete and checkable.

1. Never commit secrets or read secret material into context.
2. Behavior changes land with tests, written first. Prefer larger-scoped
   tests against real dependencies over narrow mocks.
3. Agents never commit, push, merge or deploy on their own - a human
   triggers each of those explicitly. Sole exception: a contained
   unattended run may commit checkpoints on its own
   `gnhf/` branch; push, merge and deploy remain human-only everywhere.
4. Never push to protected branches; never force-push them. Deploys happen
   by merging, never by hand.
5. Red is fixed now: a failing or flaky lint or test gets fixed when seen,
   regardless of who caused it.
6. `<fill in: project invariants, one checkable line each>`

## Enforcement map

A rule that exists only in prose is a wish. Every guardrail
is backed by at least one mechanism that does not depend on the agent's
cooperation. This framework ships the harness layer; the repository layer
(branch protection, CI, scanners) is the adopting project's and gets filled
in here during adoption.

Each Mechanism cell therefore names exactly one of three things, and
`framework/scripts/test_framework_contract.py` checks which: a mechanism that
exists in this repository, a dated deferral the framework itself can act on,
or - for a limit only the adopting project can defend - the adoption step that
fills it in, marked `Adopter-owned`. Prose alone fails the suite.

| Limit | Mechanism |
|---|---|
| No secrets | Deny-list on secret paths in `.claude/settings.json` (`.env`, `.env.*`, `*.pem`, `*serviceaccount*.json`, `*.key`, SSH private keys), asserted by `framework/scripts/test_framework_contract.py`. That list binds the `Read` tool only, so `framework/scripts/gnhf_guard.py` enforces the same names against Bash in unattended runs - `cat .env` is blocked, not just `Read(.env)` - and `framework/scripts/test_gnhf_guard.py` asserts the two lists cannot diverge. Both are enumerations: a secret under a name nobody listed is still readable. Repository-layer scanning is Adopter-owned (`framework/skills/adopt-framework/SKILL.md` step 7) |
| No autonomous commit/push/deploy | Commit, push, merge, tag, deploy and every `gh` write subcommand are absent from the allowlist in `.claude/settings.json`, so the harness prompts a human; asserted by `framework/scripts/test_framework_contract.py`; `framework/scripts/gnhf_guard.py` blocks them in unattended runs, where prompts are bypassed |
| No force-push, no hand deploys | Force-push is deny-listed in `.claude/settings.json` and the deny list is asserted unshadowed by `framework/scripts/test_framework_contract.py`; `framework/scripts/gnhf_guard.py` blocks remote git unattended; remote-side `<fill in by 2027-03-31: branch protection on every protected branch>` |
| Green before merge | `make test` run locally before any commit; `<fill in by 2027-03-31: CI re-running make test on every PR>` |
| Unattended runs stay local | gnhf settings profile deny-lists everything remote/external; `framework/scripts/gnhf_guard.py` hook blocks network commands even with prompts bypassed, and confines writes to the repo along both paths that create a file: the `Edit`/`Write`/`NotebookEdit` tools, and shell redirection (`echo x > /tmp/out` is blocked). A write carried in a command's own arguments (`cp`, `tee`, `dd of=`) is not confined. Defense, not proof - the residual holes are listed in `framework/knowledge/gnhf-safe-subcommands.md` and need network isolation to close |
| Docs stay in sync with code | `make reconcile` (the external [knowform](https://pypi.org/project/knowform/) CLI, source github.com/AndyLan0503/knowform; `make setup` installs it, pinned `>=0.3,<0.4`) reports doc↔code drift from the bindings in `knowform.bindings.json` against hashes recorded in `knowform.lock`; `framework/scripts/test_knowledge_cards.py` asserts every sourced card is bound, so the reconciler cannot pass by scanning nothing; non-blocking until the judge is trusted, then a PR check |
| Python 3.9 floor | `framework/scripts/test_framework_contract.py` parses every module under `framework/scripts/` at the 3.9 language level and rejects PEP 604 annotations that lack `from __future__ import annotations` |
| This table is self-checking | `framework/scripts/test_framework_contract.py` parses this table and fails any row that cites a path or `make` target which does not exist, defers without a real calendar date, or - in this repository only - defers past that date |
| XP test-first | Guardrail 2 + the "How tested" section and test-first checkbox in `.github/pull_request_template.md` |
| XP continuous integration | Guardrail 5 + `make test` gate (local); `<fill in by 2027-03-31: CI re-running make test on every PR>` |
| Tooling Python is not the floor Python | `framework/scripts/test_framework_contract.py` fails a `make setup` recipe that installs knowform with `pip` or `python3 -m pip` - both the 3.9 floor, below knowform's 3.10 minimum - and fails a `make reconcile` that calls a knowform other than the one `setup` installed |
| XP pairing | implementer != reviewer, structurally: review is dispatched to a different agent than the one that wrote the diff (`framework/skills/conduct-pipeline/SKILL.md`, separate shims under `.claude/agents/`). Reviewer read-only is a dispatch instruction the harness does not enforce - see "Reviewer access" |
| Project invariants | Adopter-owned: guardrail 6 is filled during adoption (`framework/skills/adopt-framework/SKILL.md` steps 2 and 4) and each invariant rides into every review on the checklist line in `.github/pull_request_template.md` |

When adding a guardrail, wire its mechanism in the same change.

## Harness adapters

The rules above are harness-agnostic; each harness gets two thin bindings
and nothing more:

- **Pointer file** - CLAUDE.md (imports this file), GEMINI.md,
  `.cursor/rules/agents.mdc`, `.github/copilot-instructions.md`. Content in
  a pointer beyond the pointer is a bug.
- **Permission policy** - allow the exact read-only and local commands agents
  actually run (`make` targets by name, `git status/diff/log`, read-only
  `gh pr`/`gh issue` subcommands), deny destructive ones, and leave commit,
  push, merge, tag, deploy and every `gh` write subcommand unlisted so the
  harness asks a human. Wildcards over a command family are not a policy:
  `Bash(make *)` allows any target and the Makefile is editable, and
  `Bash(gh pr *)` reaches `gh pr merge`. Claude Code: `.claude/settings.json`
  (committed, team-wide) and `.claude/settings.local.json` (gitignored,
  personal). Mirror the same policy in any other harness a teammate uses.
  Known residue: `Bash(git branch*)` also auto-approves `git branch -D`. It is
  local, recoverable from the reflog, and allowed deliberately - narrow it if
  your project disagrees.
- **Role bindings** - thin shims that point at `framework/roles/`.
  Claude Code: `.claude/agents/`. Other harnesses: hand the role file to a
  fresh session with only the access its frontmatter declares.
- **Command bindings** - same pattern for procedures: Claude Code's
  `/ship` (`.claude/commands/ship.md`) is a pointer to
  `framework/skills/conduct-pipeline/SKILL.md`; any other harness runs the skill by
  being told to follow it.

## Commands

Make targets are the canonical entrypoints for humans, agents and CI alike -
nobody retypes pipelines by hand.

- `make help` - list the targets; the default goal, so bare `make` runs it
- `make setup` - one-time local setup: builds `.venv-tools` from a Python
  >= 3.10 and installs knowform into it. Deliberately *not* auto-approved: it
  installs from PyPI, so `/ship` and adoption prompt a human here
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
implementer never reviews their own change - review is dispatched to a
different agent than the one that wrote the diff. Reviewer roles declare
`access: read-only`; read the next section before relying on that.

### Reviewer access

Two claims used to travel as one. Only the first of them is true.

- **The implementer/reviewer split is structural.** The conductor dispatches
  review to a different agent, with its own context and its own role file, so
  a role cannot review itself. That holds without anyone's cooperation.
- **Reviewer read-only is not enforced.** The reviewer shims in
  `.claude/agents/` declare `tools: Read, Grep, Glob, Bash`, and Bash writes
  (`sed -i`, `>`, `rm`). A security-reviewer dispatched read-only has been
  observed writing a file during an audit and reporting that it had; nothing
  stopped it. The `access: read-only` line is an instruction the agent
  follows - the exact standard the enforcement map exists to beat.

Bash stays. Every blocker worth having came from a reviewer that executed
something: running an adversarial payload against the guard, mutating a fix in
memory to prove the test would fail on revert. A reviewer reporting from
reading code is how plausible-but-wrong findings survive.

The operational consequence, until a mechanism exists: **treat any file a
reviewer changed as an unreviewed diff.** `git status` after a review is part
of the review.

Two honest ways to close it, neither implemented:

1. A harness-enforced read-only command allowlist for reviewer bindings - the
   reviewer keeps Bash, but only for commands that cannot write.
2. A separate, explicitly write-capable verifier role the reviewer invokes
   when a finding needs execution to confirm, whose output is a diff that goes
   back through review like any other.

### Extreme Programming (XP) disciplines

The repo already runs several XP practices; this names them and maps each to
the guardrail, role or mechanism that carries it. This subsection is additive -
it changes no guardrail wording (guardrails 1-6 are cited by number elsewhere).

Enforced (a cooperation-free mechanism exists - see the Enforcement map):

- **Test-first** - guardrail 2 (behavior changes land with tests, written
  first) plus the PR template "How tested" / test-first checkbox.
- **Continuous integration / green-before-merge** - guardrail 5 (red is fixed
  now) plus the `make test` gate.
- **Pairing** - the implementer != reviewer role split (structural): review is
  dispatched to a different agent than the one that wrote the diff. The
  read-only half is a dispatch instruction, not an enforced limit - see
  "Reviewer access".

Conventions (encouraged, but no cooperation-free mechanism today, so not
guardrails):

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
keeping lives in a committed file:

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
- Tooling scripts: Python over shell, unit-tested, stdlib-first, and running
  on Python 3.9.6 - the stock macOS interpreter a new adopter runs `make test`
  with before installing anything. `framework/scripts/test_framework_contract.py`
  parses every module at that language level. PEP 604 `X | Y` annotations are
  evaluated at runtime on 3.9 and raise TypeError there, so any module using
  them must open with `from __future__ import annotations`; the test enforces
  that pairing rather than banning the syntax.
- Knowledge cards follow OKF (Open Knowledge Format); the format authority is
  `framework/knowledge/README.md`.
- A tool that needs a newer Python than the floor gets its own interpreter,
  never a raised floor: `make setup` builds `.venv-tools` from a Python >= 3.10
  for knowform, and `make reconcile` runs that copy by path. The two
  interpreters are separate on purpose, and
  `framework/scripts/test_framework_contract.py` fails a `setup` recipe that
  installs knowform with `pip` / `python3 -m pip` instead.
