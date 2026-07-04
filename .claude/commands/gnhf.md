---
description: Good night, have fun - run the pipeline fully unattended in a contained session. From a normal session, launches the contained run in the background.
allowed-tools: Task, Read, Edit, Write, Grep, Glob, Bash
---

Request:

$ARGUMENTS

Two cases, by how this session was started:

- **This session is already contained** (launched by `scripts/gnhf.py` or
  `claude --settings .claude/gnhf-settings.json` - permission prompts are
  bypassed): follow `skills/unattended-run/SKILL.md` for the request
  directly. This command adds nothing to the skill (docs/adr/0001).
- **This is a normal session** (prompts active): do NOT run the skill here.
  Launch the contained run in the background instead:

      python3 scripts/gnhf.py "<request>"

  Report that it is running, where its checkpoints will land
  (`gnhf/<feature-slug>` branch, HANDOFF.md), and that the human reviews
  and pushes per docs/running-the-pipeline.md.
