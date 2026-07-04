# agentic-framework

A minimal, harness-agnostic scaffold for running a disciplined agentic
SDLC: agents kept inside safe rails, roles and procedures portable across
harnesses, and collaboration state that outlives any chat session.

## The four ideas

1. **One source of truth for agent behavior.** All rules live in
   `AGENTS.md`. Claude Code, Gemini CLI, Cursor and Copilot each get a thin
   pointer file, never content. A rule change touches one file.
2. **Limits are mechanisms, not prose.** Every guardrail is backed by
   something that works even when the agent is confused: permission
   allow/deny lists, branch protection, the project's CI re-running the
   same `make test`. AGENTS.md carries an enforcement map pairing each
   rule with its mechanism. The framework ships the harness layer and the
   behavioral rules; CI workflows and hooks are the adopting project's to
   wire (docs/adr/0002).
3. **Collaboration state lives in committed files.** Decisions in
   `docs/adr/`, facts in `knowledge/` cards, feature handoffs in
   `docs/specs/`, session state in gitignored `HANDOFF.md`. Chat history
   is invisible to teammates and to the next session; files are not.
4. **Roles and skills are portable.** SDLC roles (analyst, PM,
   implementer, interrogator, security reviewer, release captain) are
   tool-neutral prompt files in `roles/`; procedures are `SKILL.md`
   runbooks in `skills/`. Harness bindings are three-line shims, so the
   same pipeline runs from Claude Code, Cursor, Gemini or a plain chat.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Source of truth: guardrails, enforcement map, roles, conventions |
| `CLAUDE.md`, `GEMINI.md`, `.cursor/`, `.github/copilot-instructions.md` | Harness pointer shims |
| `roles/` | Tool-neutral SDLC role prompts (access, inputs, outputs declared) |
| `skills/` | Reusable runbooks, one `SKILL.md` per procedure |
| `docs/agentic-sdlc.md` | The pipeline: handoffs, human gates, autonomy levels |
| `docs/running-the-pipeline.md` | How to use `/ship` and `/gnhf` day to day |
| `docs/specs/` | Feature specs - the analyst -> PM -> implementer handoff artifact |
| `docs/adr/` | Decision records + template |
| `knowledge/` | One-fact-per-card knowledge base |
| `.claude/` | Claude Code bindings: permission policy, role shims, `/ship` + `/gnhf`, gnhf containment profile |
| `.github/` | PR template mirroring the guardrails + Copilot shim |
| `scripts/` | `gnhf.py` unattended launcher + `gnhf_guard.py` containment hook, unit-tested |
| `Makefile` | Canonical entrypoints: `setup`, `test`, `e2e` |

## Onboard a project

With this repo checked out locally:

```
make adopt TARGET=/path/to/your-repo
```

Or from inside the target repo, installing straight from the remote:

```
curl -fsSL https://raw.githubusercontent.com/AndyLan0503/agnostic-agent-framwork/main/scripts/adopt.py | python3 - . --from https://github.com/AndyLan0503/agnostic-agent-framwork
```

The installer clones the framework to a temp dir and adopts from it,
recording the framework commit in the target's `.framework-version`
(commit that file). Re-running the same command later is the update path,
resolved per file against that base:

- framework changed, you didn't touch the file -> fast-forwarded (`^`)
- you customized it, framework unchanged -> kept, silently (`=`)
- both changed -> kept, new version lands as `.framework-new` to merge (`!`)

Your filled-in AGENTS.md, Makefile and permissions stay quiet across
updates unless the framework actually changed them.

Works for new and existing repos: nothing is ever overwritten, and where
an existing file differs the framework version lands beside it as
`<name>.framework-new` to merge from. Then `skills/adopt-framework/SKILL.md`
walks the rest - merge the conflicts (fold an existing CLAUDE.md into
AGENTS.md, wrap existing build commands in the Make target names, union
permissions), fill the `<fill in>` placeholders, split the implementer per
stack, wire branch protection and CI, seed knowledge and ADRs. It ends
with a verification checklist; the whole thing is agent-runnable - tell an
agent in the target repo to "follow skills/adopt-framework/SKILL.md".
