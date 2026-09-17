---
name: adopt-framework
description: >-
  Onboard the agentic-framework scaffold into a new or existing repository.
  Use when standing up the framework (AGENTS.md, roles, skills, gnhf
  containment, collaboration artifacts) in a project. Covers copying,
  filling placeholders, wiring enforcement, and verifying the result.
---

# Onboard the framework

Invariants to preserve:
- AGENTS.md stays the single source of truth; harness files stay pointers.
- Existing project files are never overwritten by the scaffold.
- Every guardrail gets a mechanism in the enforcement map, not just prose.

## Steps

1. **Copy the scaffold.** From a local framework checkout:
   `python3 framework/scripts/adopt.py /path/to/repo` - or from inside the
   target repo, straight from the remote:
   `curl -fsSL <raw-url>/framework/scripts/adopt.py | python3 - . --from <framework-git-url>`.
   Nothing is overwritten; where an existing file differs from the
   framework's, the framework version lands beside it as
   `<name>.framework-new`. In an existing repo, merge each one (an agent
   in the target repo can do this - point it at this step):
   - **CLAUDE.md / GEMINI.md / Cursor rules / Copilot instructions with
     real content**: move the durable content into AGENTS.md sections
     (guardrails, commands, conventions), then reduce the file to the
     framework's pointer shim.
   - **Makefile**: keep the project's build system; add the framework's
     `setup` / `test` / `e2e` target names as wrappers around existing
     commands so hooks, docs and roles keep working.
   - **`.claude/settings.json`**: union the permission lists - keep
     project allows, add the framework's denies.
   - **Existing framework/docs/adr/**: keep the project's decision log as is;
     the scaffold ships only `0000-template.md` and the directory README.
   Delete each `.framework-new` once merged.
   Then **restart the session.** `.claude/agents/` shims are registered when a
   session starts, so the ones just copied do not exist in the session that
   copied them - the first `/ship` fails on every role with "agent type not
   found". Until you restart, use the fallback AGENTS.md already states: hand
   the role file to a fresh generic agent with only the access its frontmatter
   declares.
2. **Fill AGENTS.md.** Replace every `<fill in>`: project invariants under
   Guardrails, enforcement map rows, commands, protected branches and
   branch model under Git and GitHub behavior. Delete the placeholder
   note at the top.
3. **Wire the Make targets.** Point `setup`, `test`, `e2e` at the
   project's real commands, keeping the target names. Keep the shipped
   `framework/scripts/test_*.py` in the `test` body - they guard the guard.
4. **Fill the PR template** invariants line so the checklist mirrors the
   Guardrails.
5. **Tune permissions.** Extend `.claude/settings.json`: allow the
   project's routine commands, deny its destructive ones. If the project
   adds CLIs with remote reach, extend the gnhf deny list and
   `SAFE_BASH` in `framework/scripts/gnhf_guard.py` - test-first, per
   framework/knowledge/gnhf-safe-subcommands.md.
6. **Split the implementer** (`framework/roles/implementer.md`) into per-stack
   variants (api, ui, infra) once the project has distinct stacks, with
   matching shims in `.claude/agents/`; infra variants stay plan-only.
7. **Wire the repository layer** the enforcement map calls for: branch
   protection on protected branches, CI running `make test` on every PR,
   secret scanning. Record each in the map, and replace the shipped deferral
   dates with dates your team chose - until you do, the expiry check stays
   skipped in your repository (CONTRIBUTING.md, "Adding an enforcement-map
   row"). `make reconcile` is the shipped "docs stay in sync" mechanism -
   non-blocking by default; wire it into CI beside `make test` once the judge
   is trusted.
   Two rules for every check you add here:
   - **Write the check before the thing it checks.** An allowlist or scanner
     written after the dependencies are in place rubber-stamps whatever is
     already there.
   - **Every check reports what it examined** - a count of files, packages or
     rows - and ships a test that fails when that count is zero for the wrong
     reason. A check keyed to a literal directory name, a single file
     extension, or an absolute-path ignore list passes forever while scanning
     nothing. See `framework/knowledge/checks-report-what-they-examined.md`.
8. **Seed the artifacts.** Write knowledge cards for the 3-5 facts a
   newcomer gets wrong first; add an ADR for any standing architecture
   decision, numbered from 0001.
   Cards follow OKF (Open Knowledge Format); `framework/knowledge/README.md` is the
   format authority (required `type`; use `timestamp`, not `updated`). To
   add card types beyond `{convention, mechanism}`, extend `TYPE_VOCAB` in
   `framework/scripts/test_knowledge_cards.py`. A card body is one `## Fact`
   section; a sourced card gets one `code-is-truth` entry per `sources` path in
   `knowform.bindings.json` so its claim is drift-governed (pattern:
   `framework/knowledge/gnhf-safe-subcommands.md`). Keep the `knowform` pin in
   `make setup` - an unpinned upgrade past a binding-model change reads zero
   bindings and still exits 0 - and keep it installing into `.venv-tools` from
   a Python >= 3.10, separate from the interpreter the suites run on.
9. **Verify.**
   - `make setup && make test` green. `make setup` is deliberately not
     auto-approved - it installs from PyPI - so it prompts a human here.
   - Guard smoke test from the repo root:
     `echo '{"tool_name":"Bash","tool_input":{"command":"git push"}}' | CLAUDE_PROJECT_DIR=$PWD python3 framework/scripts/gnhf_guard.py`
     must exit 2.
   - Ask an agent in a fresh session: "what are the guardrails here?" -
     the answer should come from AGENTS.md.
   - A red suite in a fresh adoption is a framework bug, not yours: the
     framework's own `framework/scripts/test_adoption_smoke.py` runs the whole
     suite inside a synthetic adopted copy, so anything that reaches you here
     escaped that net. Report it upstream rather than working around it.

**Updating later:** re-run the same install command. The recorded
`.framework-version` (commit it with the scaffold) enables per-file
three-way resolution: untouched files fast-forward, your customizations
stay quiet, and only genuine two-sided changes land as `.framework-new`
to merge. After merging a conflicted file, delete the `.framework-new`.

For a large existing repo, adopt incrementally in this order, verifying
each layer before the next: AGENTS.md + shims + permissions first (agents
behave immediately), then roles/skills and the pipeline, then gnhf last -
only once `make test` is trustworthy, since unattended runs stand on it.

## Done when

- No `<fill in>` remains in AGENTS.md or the PR template, and no
  `*.framework-new` files remain.
- `make test` is green and includes the framework's script tests.
- Every enforcement map row names a real mechanism.
- Harness rule files are pointers only.
- A dry-run `/ship` on a toy request walks the pipeline and stops at the
  gates.
