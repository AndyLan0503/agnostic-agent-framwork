# Running the pipeline: /ship and /gnhf

Two ways to run the same pipeline (docs/agentic-sdlc.md). `/ship` keeps you
in the loop at every gate; `/gnhf` replaces gates with containment and runs
alone. Rule of thumb: `/ship` while you're at the keyboard, `/gnhf` when
you're leaving - and only `/gnhf` a kind of task `/ship` has already proven
the repo handles well.

|  | `/ship` (Level 1) | `/gnhf` (Level 2) |
|---|---|---|
| You are | present, answering gates | gone |
| Gates | scope, P0 slice, final push | none - conservative assumptions, recorded |
| Git | agent never commits | checkpoint commits on a `gnhf/` branch, never pushes |
| Network | normal session permissions | none - guard + deny profile |
| Prompts | normal permission flow | bypassed inside containment |
| Output | working-tree diff + spec | branch + HANDOFF.md |

## /ship

```
/ship add CSV export to the reports page
```

Any other harness: "Follow skills/conduct-pipeline/SKILL.md for: <request>".

Before starting: clean working tree on a feature branch, `make test` wired
and green. One feature per run; a small fix doesn't need the pipeline -
just fix it.

What to expect - you'll be interrupted exactly three times:

1. **Scope gate** (after analysis): the open questions the analyst couldn't
   answer from the code. Answer tersely; "out of scope" is a fine answer.
2. **P0 gate** (after spec): the smallest shippable slice. Push back here,
   not during implementation - scope changes are cheap now, expensive later.
3. **Final gate**: summary, test evidence, residual review findings. You
   review the diff, then commit/push yourself - the agent can't.

Steering tips:

- The spec file is the steering wheel. If implementation is drifting, stop,
  edit `docs/specs/<feature>.md`, and redispatch the implementer - don't
  argue with the implementer in chat.
- Interrupted or out of context? Nothing is lost: the spec and diff are on
  disk. Start a fresh session and point it at the spec file.
- Reviewer findings route back to the implementer automatically; you only
  hear about what survives or gets accepted as residue.

## /gnhf

```
python3 scripts/gnhf.py "add CSV export to the reports page; \
  acceptance: exported file matches the visible table, covered by an e2e test"
```

The script is the canonical entrypoint - it loads the containment profile
and handles usage-limit pauses. Three ways to start a run:

- **Terminal**: `python3 scripts/gnhf.py "<request>"` from the repo root.
- **From a normal Claude Code session**: type `/gnhf <request>` - the
  command notices prompts are active and launches the script in the
  background instead of running the skill in-session (the launch command
  is allowlisted, so it doesn't prompt). You keep your session; the run
  reports through its branch and HANDOFF.md.
- **Contained interactive session**: `claude --settings
  .claude/gnhf-settings.json`, then `/gnhf <request>`. Same containment,
  no prompts, but you watch it live - and you give up the launcher's
  automatic sleep-and-resume across usage-limit windows, so prefer this
  for supervising, not for overnight.

Write the request like a mini-spec. There is no scope gate, so every
ambiguity gets the most conservative reading. The more acceptance criteria
you state, the less it has to assume. A vague request produces a small,
overly-safe slice - that's by design.

While it runs: usage-limit windows are slept through and the session
resumes itself (`--max-waits`, default 8). Checkpoint commits mean a crash
or limit pause loses nothing.

The morning review ritual:

1. Read `HANDOFF.md` - what was built, every assumed answer, residual
   findings, or where and why it stopped early (an honest early stop is a
   success, not a failure).
2. `git log --oneline` on the `gnhf/` branch - checkpoints tell the story.
3. `make test` yourself - trust the mechanism, not the report.
4. Optionally dispatch the interrogator role on the branch diff for a
   fresh adversarial pass.
5. Satisfied? Push and open the PR yourself. Not satisfied? The branch is
   throwaway by construction - delete it or mine it for the spec.

Containment (docs/adr/0002): edits confined to the repo, nothing remote,
no external connections, local testing only. For untrusted inputs, run the
launcher inside a network-isolated container - the guard is defense, not
proof.

## Failure modes to know

- **/ship stalls at a gate**: it's waiting for you; gates never time out.
- **/gnhf stopped early**: read the blocker in HANDOFF.md - usually an
  ambiguity it refused to guess on. Answer it in the request and relaunch.
- **Review loop residue**: both modes cap implementer-reviewer loops
  (3 per reviewer in gnhf) and surface what remains rather than looping
  forever. Residual findings are yours to judge.
