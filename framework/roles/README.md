# Roles

Tool-neutral SDLC role definitions - one prompt file per role, usable from
any harness. The pipeline connecting them is
framework/docs/agentic-sdlc.md.

## File format

```markdown
---
name: <kebab-case role name>
description: <one line - what this role does>
access: read-only | read-write
inputs: <what the role is handed, explicitly - roles start cold>
outputs: <the durable artifact the role produces>
---

The role prompt, written to the agent in second person.
```

## Binding a role in your harness

The role file is the source of truth; bindings are thin shims that add
nothing (same pattern as AGENTS.md).

- **Claude Code**: a shim subagent in `.claude/agents/<name>.md` whose body
  says "read `framework/roles/<name>.md` and follow it"; its `tools:` frontmatter
  enforces the role's `access` level mechanically.
- **Any other harness** (Cursor, Gemini CLI, Codex, a plain chat): start a
  fresh session or subagent, give it the role file plus the inputs listed
  in the frontmatter, and grant only the access the frontmatter states.

## Rules that make roles work

- **Roles are hats, not people.** One human or agent can wear several, but
  never implementer and reviewer on the same change.
- **Roles start cold.** Hand them artifact paths and a request summary
  explicitly; never assume they can see prior conversation.
- **`access` is honoured by the binding as far as the harness can express
  it - and no further.** Reviewer roles declare `access: read-only`, and a
  binding drops every write tool it can: Claude Code's `tools:` frontmatter
  omits Edit and Write. It does not omit Bash, and Bash writes (`sed -i`,
  `>`, `rm`). Reviewers keep Bash on purpose - a finding confirmed by running
  something beats a finding read off the page - so read-only is enforced for
  the file-writing tools and requested for Bash. What is structural is the
  split itself: review goes to a different agent than the one that wrote the
  diff. Treat any file a reviewer changed as an unreviewed diff. AGENTS.md
  "Reviewer access" has the full statement and the two ways to close it.
