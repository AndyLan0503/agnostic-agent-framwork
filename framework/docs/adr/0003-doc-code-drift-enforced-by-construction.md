# ADR-0003: Doc↔code drift is enforced by construction

- **Status:** Proposed
- **Date:** 2026-07-12
- **Deciders:** framework authors

## Context

ADR-0002 established the framework's thesis: a rule that exists only in prose
is a wish, so every guardrail is backed by a mechanism that does not depend on
agent cooperation. The collaboration-artifacts convention - `framework/knowledge/` cards
and `framework/docs/specs/` stay in sync with the code they describe, updated in the same
PR that changes the fact - is currently exactly such a wish. It has no row in
the AGENTS.md enforcement map. Nothing detects when a `.md` claim rots because
the code moved out from under it.

Doc↔code drift is the failure mode this framework is most exposed to: the whole
repository is prose-about-code, and agents author both sides. The gap needs a
mechanism, and that mechanism should dogfood on this repo's own corpus.

The mechanism is a **doc↔code drift reconciler** modelled on Terraform. The
open question is not whether to build it but how to bind docs to code, how to
declare which side is authoritative, and how to keep the common case free.

## Decision

We will host a doc↔code drift reconciler in this repo as a self-contained
Python subpackage (`framework/scripts/reconcile/`), and add its check as the enforcement
mechanism for the collaboration-artifacts convention in the AGENTS.md map.

Model, three states from Terraform:

- **desired** - prescriptive docs (specs, plans); code should conform to them.
- **recorded** - a `.docstate` lockfile: per-binding content hashes plus the
  last judged verdict.
- **actual** - the code.

Drift is `recorded` vs `actual`; a plan is `desired` vs `recorded`.

Three resolved decisions (the M0 open questions):

1. **Truth-direction is explicit, never inferred.** Every managed doc declares
   `direction: code-is-truth | doc-is-truth | manual` in frontmatter. Location
   heuristics are too brittle for a guardrail; misclassifying direction would
   auto-write the wrong side.
2. **Bindings are anchored region + hash**, not whole-file path-globs. A
   binding ties a specific doc region to a specific code region via named
   anchors, and the lockfile hashes each side. This costs more to author but
   gives precise blast-radius from M1 and makes M2's 3-way diff (code moved /
   doc moved / both = conflict) granular from the start rather than a later
   retrofit.
3. **Python**, stdlib-first, matching this repo's conventions (`gnhf.py`,
   `adopt.py`), dogfooding on a Python corpus, with tree-sitter and LLM
   clients first-class.

Cost is controlled by a tiered cascade, cheapest first, so the common case is
free: Tier 0 hash-gate + `git diff` (unchanged region cannot have drifted →
zero LLM calls); Tier 1 free structural-graph blast-radius scoping; Tier 2
embeddings triage; Tier 3 LLM judge only on survivors, fed tight
neighborhoods. The structural graph is disposable and rebuildable, never
hand-maintained. No semantic/concept knowledge-graph is built first; that
layer is deferred, optional, and evidence-gated (M5).

`apply` fixes the **safe direction only** - regenerating descriptive prose from
code. Prescriptive drift (code diverged from a `doc-is-truth` spec) is surfaced
for a human and never written back into code.

## Alternatives considered

- **Inferred truth-direction** (path heuristics) - zero annotation burden, but
  a wrong inference silently corrupts the authoritative side; rejected for a
  guardrail.
- **Path-glob bindings** (the handoff's M1 leaning) - simpler to author, but
  whole-file granularity forces a later, disruptive retrofit to get 3-way diff;
  we pay the authoring cost now to keep the state model honest throughout.
- **Standalone tool / separate repo** - loses the dogfooding corpus and the
  framework-shape fit (skill + command shim + Make target + `adopt.py`
  distribution). Subpackage boundary keeps the graduation path open.
- **Semantic knowledge-graph first** - LLM-heavy to extract and itself drifts;
  the near-free structural layer is likely ~90% of the value.
- **Prose-only convention** (status quo) - the wish ADR-0002 exists to abolish.

## Consequences

The collaboration-artifacts convention gains a real enforcement row: a
`reconcile plan` check can gate PRs once the judge is trusted (M4). Managed
docs must carry frontmatter and anchors, and drift-relevant PRs will surface a
plan. Success is defined by four invariants: no alarm fatigue (judge tuned for
precision over recall); most runs cost zero tokens; truth-direction always
explicit; graph always disposable. If the judge cannot hit precision without
crying wolf (proven or disproven in M1), the whole approach is revisited before
any CI wiring. The M0 schema (`framework/docs/specs/reconcile.md`) is the contract every
later milestone inherits; changing it after M2 is expensive, so it is specified
before code.
