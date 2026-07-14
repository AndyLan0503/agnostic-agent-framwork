# ADR-0002: Agent limits are enforced by construction, not prose

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** framework authors

## Context

Prompts are soft: an agent can be talked, confused or injected past an
instruction like "never push to main". A behavior limit is only as strong
as its weakest enforcement point. This bites hardest in unattended runs,
where permission prompts must be off but limits must hold with nobody
watching.

## Decision

Every guardrail is backed by a mechanism that does not depend on the
agent's cooperation, recorded rule-by-rule in the AGENTS.md enforcement
map.

Attended sessions: harness permission policy (routine commands
allowlisted, destructive ones deny-listed, commit/push/deploy simply
absent so the harness asks a human) plus the PR template checklist. The
repository layer - branch protection, CI re-running `make test`, secret
scanning - is wired per project during adoption; the framework ships no
CI workflows or git hooks because platforms differ and templates rot.

Unattended runs (Level 2) launch only through `framework/scripts/gnhf.py`, whose
settings profile bypasses prompts inside containment:

- Deny rules for everything remote or external: push/pull/fetch, gh,
  cloud CLIs, network commands, web tools, registry writes, secret reads.
- A PreToolUse guard (`framework/scripts/gnhf_guard.py`) that fires regardless of
  permission mode: edits confined to the launching repo, the same
  remote/network classes blocked, with a whole-command-match allowlist
  for local-only subcommands (framework/knowledge/gnhf-safe-subcommands.md).
- Local checkpoint commits on a `gnhf/` branch - the sole relaxation of
  the no-autonomous-commits guardrail; push, merge and deploy stay
  human-only.
- The launcher sleeps through usage-limit windows and resumes.

The guard is defense, not proof: for hostile inputs, run the launcher in
a network-isolated container as the outer wall.

## Alternatives considered

- **Prompt-only rules** - cheapest; fails exactly when a confused or
  injected agent matters most.
- **Container-only containment** - a hard wall, but platform-specific and
  heavier; recommended as an addition, not a replacement.
- **Shipping CI/hooks in the framework** - every org differs; the
  enforcement map keeps the obligation without dictating implementation.

## Consequences

Gates hold even against a convinced agent, and the blast radius of a bad
unattended run is bounded to local commits on a throwaway branch. Costs:
new guardrails must be wired to a mechanism in the same change, and the
guard's blocklists need maintaining as the project adopts new tools.
