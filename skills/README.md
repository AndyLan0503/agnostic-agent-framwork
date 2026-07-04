# Skills

Reusable procedures - step-by-step runbooks any agent in any harness (or a
human) can follow. When a workflow has been done twice from memory, the
second time it becomes a skill.

Skills follow the open Agent Skills convention: one directory per skill
containing a `SKILL.md`, so most harnesses can load them natively and the
rest can simply be told to read the file.

## Format

```markdown
---
name: <kebab-slug, matches the directory name>
description: >-
  What the skill does AND when to use it - agents decide from this line
  alone whether to load the skill, so make it specific.
---

# <Title>

Invariants to preserve:
- <rules that must survive the procedure>

## Steps

1. <numbered, concrete, checkable>

## Done when

- <observable completion criteria>
```

## Conventions

- Portable by construction: no personal paths, no machine-specific values;
  reference `make` targets and repo-relative paths only.
- A skill that needs project placeholders marks them `<fill in>` like
  AGENTS.md does.
- Claude Code: project skills are discovered under `.claude/skills/`;
  symlink or copy this directory there if you want autoloading. Any other
  harness: point the agent at the `SKILL.md` path.
