# Doc↔code drift reconciler

Terraform for agentic docs: detect when `.md` docs drift from the code they
describe, propose a plan, and apply fixes in the safe direction only. Hosted as
`scripts/reconcile/` per docs/adr/0003. This spec is **M0**: the schema every
later milestone inherits. Design only - no code here.

## Analysis

- **Problem** - `knowledge/` cards and `docs/specs/` are prose-about-code that
  rots when code moves. The convention that they stay in sync (docs/adr/0001)
  has no enforcement; it is the wish ADR-0002 exists to abolish.
- **User stories**
  - As an agent editing code, I want drift surfaced on my diff so I fix the doc
    in the same PR instead of leaving a silent lie.
  - As a reviewer, I want a scoped, cheap drift report - not a re-scan of every
    doc on every commit.
  - As a maintainer, I want to bless an intentional divergence once, without
    the tool nagging about it again.
- **Acceptance criteria**
  - Given an unchanged governed region, When `reconcile plan` runs, Then it
    makes zero LLM calls and reports no drift.
  - Given code changed under a `code-is-truth` binding, When `plan` runs, Then
    the affected binding is flagged with the specific claim at risk.
  - Given a `doc-is-truth` binding whose code diverged, When `apply` runs, Then
    it refuses to touch code and surfaces the conflict for a human.
- **In scope (M0)** - the schema: frontmatter fields, `direction` enum,
  `.docstate` lockfile format, graph node/edge types.
- **Out of scope (M0)** - detector, lockfile writer, apply, CI wiring, semantic
  graph. Those are M1-M5.
- **Guardrails touched** - collaboration-artifacts convention (new enforcement
  row); no autonomous writes to code (apply is safe-direction only).
- **Open questions** - resolved in docs/adr/0003 (explicit direction; anchored
  region + hash bindings; Python).

## Spec

### Goal

Define the data contract binding docs to code so M1-M5 build against a stable
schema. Non-goal: any runtime behavior.

### Three states

| State | What | Where |
|---|---|---|
| desired | prescriptive docs (code should conform) | `.md` with `direction: doc-is-truth` |
| recorded | last-blessed hashes + verdict | `.docstate` lockfile |
| actual | the code | working tree / git |

Drift = recorded vs actual. Plan = desired vs recorded.

### Frontmatter (per managed doc)

```yaml
---
reconcile:
  direction: code-is-truth   # | doc-is-truth | manual
  bindings:
    - doc_anchor: overview          # named region in THIS doc
      governs: scripts/gnhf.py      # file or glob the region describes
      code_anchor: "def main"       # optional: narrow to a symbol/region
---
```

- `direction`
  - `code-is-truth` - descriptive prose; `apply` may regenerate it from code.
  - `doc-is-truth` - prescriptive; code must conform; drift surfaced, never
    auto-applied to code.
  - `manual` - tracked for hashing/plan, but never auto-applied either way.
- `bindings` - one or more region↔code links. A doc with no bindings is
  unmanaged and ignored.

### Anchors (region + hash bindings, per docs/adr/0003)

A binding ties a **doc region** to a **code region**; the lockfile hashes each.

- **doc_anchor** - a named region in the markdown. Delimited by HTML-comment
  fences so anchors survive rendering:
  ```markdown
  <!-- reconcile:overview:start -->
  ...prose governed by this binding...
  <!-- reconcile:overview:end -->
  ```
  Absent fences → the anchor spans the whole doc (degrades to file-level).
- **code_anchor** - optional. A symbol path or line-range narrowing `governs`.
  Resolved to a concrete region by the (free) structural layer; absent → the
  whole matched file(s).

Both resolve to a normalized text span whose hash is the unit of drift.

### `.docstate` lockfile (recorded state)

One file at repo root, JSON, human-diffable, machine-written by `sync`/`apply`
(M2+). Never hand-edited in practice, but greppable.

```json
{
  "version": 1,
  "bindings": {
    "knowledge/gnhf-safe-subcommands.md#overview": {
      "direction": "code-is-truth",
      "governs": "scripts/gnhf_guard.py",
      "doc_hash": "sha256:…",
      "code_hash": "sha256:…",
      "last_verdict": "in-sync",
      "blessed_at": "<git-sha>"
    }
  }
}
```

- Key = `<doc-path>#<doc_anchor>`, stable across content edits.
- `doc_hash` / `code_hash` - normalized-span hashes; the Tier-0 gate compares
  these against `actual`.
- `last_verdict` - `in-sync | doc-drift | code-drift | conflict | unjudged`.
- `blessed_at` - git sha at last `sync`/`apply`, for provenance.
- No structural graph is persisted here; the graph is disposable (M0 §graph).

### 3-way state (defined now, computed in M2)

Compare recorded hashes to actual:

| doc changed | code changed | verdict | plan action |
|---|---|---|---|
| no | no | in-sync | none (Tier-0 exit) |
| no | yes | code-drift | judge; `apply` if `code-is-truth` |
| yes | no | doc-drift | surface; human confirms via `sync` |
| yes | yes | conflict | surface only; never auto-apply |

### Structural graph (node/edge types; disposable, rebuilt each run)

Free layer that scopes blast-radius before any LLM call. Never persisted to the
lockfile.

- **Nodes** - `DocRegion` (a doc_anchor), `CodeRegion` (file / symbol from
  tree-sitter or LSP).
- **Edges**
  - `GOVERNS` - DocRegion → CodeRegion, from a binding.
  - `IMPORTS` / `CALLS` - CodeRegion → CodeRegion, from tree-sitter/LSP (free).
- **Blast-radius** - from the set of CodeRegions touched by `git diff`, walk
  `IMPORTS`/`CALLS` transitively bounded to depth 1-2, then follow `GOVERNS`
  backwards to the DocRegions at risk. Only those reach Tier 2/3.

### Tiered cascade (cost contract the schema must serve)

0. Hash-gate + `git diff` - unchanged span → in-sync, **zero LLM calls**.
1. Structural-graph scoping - reachable DocRegions only.
2. Embeddings triage - rank survivors.
3. LLM judge - only survivors, fed claim + bound symbol signatures, not files.

### Success metrics (invariants from docs/adr/0003)

- Most runs cost zero tokens (Tier-0 exit on unchanged corpora).
- Judge precision over recall - no alarm fatigue.
- Truth-direction always explicit in frontmatter.
- Graph never hand-maintained.

### Sequencing

- **M0** - this schema (done when accepted).
- **M1** - `plan` detector: Tier 0 → graph scope → judge on frontier. Proves
  the judge catches real drift without crying wolf. Built against this schema.
- **M2** - lockfile writer + 3-way state + `sync`.
- **M3** - `apply`, safe direction only.
- **M4** - CI/PR check + optional pre-commit hook (only after M1 judge trusted).
- **M5** - semantic graph layer, optional + evidence-gated.

### Decisions needing an ADR

Recorded in docs/adr/0003 (explicit direction; anchored region+hash; Python;
safe-direction-only apply; no-semantic-KG-first).
