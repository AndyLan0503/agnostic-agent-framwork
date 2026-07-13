# Doc↔code drift reconciler

Terraform for agentic docs: detect when `.md` docs drift from the code they
describe, propose a plan, and apply fixes in the safe direction only.
Implemented in the external [knowform](https://pypi.org/project/knowform/)
package (github.com/AndyLan0503/knowform) per framework/docs/adr/0003; this repo
is its consumer #1. This spec is **M0**: the schema every later milestone
inherits. Design only - no code here.

## Analysis

- **Problem** - `framework/knowledge/` cards and `framework/docs/specs/` are prose-about-code that
  rots when code moves. The convention that they stay in sync (framework/docs/adr/0001)
  has no enforcement; it is the wish ADR-0002 exists to abolish.
- **User stories**
  - As an agent editing code, I want drift surfaced on my diff so I fix the doc
    in the same PR instead of leaving a silent lie.
  - As a reviewer, I want a scoped, cheap drift report - not a re-scan of every
    doc on every commit.
  - As a maintainer, I want to bless an intentional divergence once, without
    the tool nagging about it again.
- **Acceptance criteria**
  - Given an unchanged governed region, When `knowform plan` runs, Then it
    makes zero LLM calls and reports no drift.
  - Given code changed under a `code-is-truth` binding, When `plan` runs, Then
    the affected binding is flagged with the specific claim at risk.
  - Given a `doc-is-truth` binding whose code diverged, When `apply` runs, Then
    it refuses to touch code and surfaces the conflict for a human.
- **In scope (M0)** - the schema: frontmatter fields, `direction` enum,
  `knowform.lock` lockfile format, graph node/edge types.
- **Out of scope (M0)** - detector, lockfile writer, apply, CI wiring, semantic
  graph. Those are M1-M5.
- **Guardrails touched** - collaboration-artifacts convention (new enforcement
  row); no autonomous writes to code (apply is safe-direction only).
- **Open questions** - resolved in framework/docs/adr/0003 (explicit direction; anchored
  region + hash bindings; Python).
- **Assumed answers (M1 detector)** - decided conservatively for the
  `knowform plan` slice, no human gate:
  - *Recorded state is not yet available* (lockfile writer is M2), so Tier-0
    uses `git diff` against a base ref (default: working tree vs `HEAD`) as the
    changed-set signal. A binding whose doc span and code region both fall
    outside the diff is `in-sync` with zero LLM calls. Normalized-span hashes
    are still computed and emitted so M2 can seed `knowform.lock`.
  - *Structural layer dogfoods on Python via the stdlib `ast` module* -
    tree-sitter/LSP are not stdlib and are deferred. A `code_anchor` that names
    a Python symbol resolves to that symbol's line span and its `IMPORTS`/
    `CALLS` neighbors; anything else (non-Python file, unresolved anchor)
    degrades to the whole file. Precision-over-recall: an unresolved anchor
    widens scope, never narrows it silently.
  - *The judge is an injected seam.* With no judge configured the plan lists
    frontier bindings as `needs-judge` and still costs zero tokens; a concrete
    `AnthropicJudge` adapter is provided but lazy-imports its client and is
    never exercised by the tests.
  - *`plan` is strictly read-only* - it emits a drift plan and touches no files
    (no lockfile, sync, apply, or CI wiring; those are M2+).

## Spec

### Goal

Define the data contract binding docs to code so M1-M5 build against a stable
schema. Non-goal: any runtime behavior.

### Three states

| State | What | Where |
|---|---|---|
| desired | prescriptive docs (code should conform) | `.md` with `direction: doc-is-truth` |
| recorded | last-blessed hashes + verdict | `knowform.lock` lockfile |
| actual | the code | working tree / git |

Drift = recorded vs actual. Plan = desired vs recorded.

### Frontmatter (per managed doc)

```yaml
---
knowform:
  direction: code-is-truth   # | doc-is-truth | manual
  bindings:
    - doc_anchor: overview          # named region in THIS doc
      governs: framework/scripts/gnhf.py      # file or glob the region describes
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

The `knowform:` block is one field of an OKF-format document: it coexists with
the OKF scalar fields (`type, title, description, tags, timestamp` and repo
extensions like `id, sources`) that a `framework/knowledge/` card carries. `knowform:`
is a declared OKF extension field (framework/knowledge/README.md), so a single card is
simultaneously an OKF document and a knowform-governed one; the parser reads
the `knowform:` block and ignores the sibling OKF scalars.

### Anchors (region + hash bindings, per framework/docs/adr/0003)

A binding ties a **doc region** to a **code region**; the lockfile hashes each.

- **doc_anchor** - a named region in the markdown. Delimited by HTML-comment
  fences so anchors survive rendering:
  ```markdown
  <!-- knowform:overview:start -->
  ...prose governed by this binding...
  <!-- knowform:overview:end -->
  ```
  Absent fences → the anchor spans the whole doc (degrades to file-level).
- **code_anchor** - optional. A symbol path or line-range narrowing `governs`.
  Resolved to a concrete region by the (free) structural layer; absent → the
  whole matched file(s).

Both resolve to a normalized text span whose hash is the unit of drift.

### `knowform.lock` lockfile (recorded state)

One file at repo root, JSON, human-diffable, machine-written by `sync`/`apply`
(M2+). Never hand-edited in practice, but greppable.

```json
{
  "version": 1,
  "bindings": {
    "framework/knowledge/gnhf-safe-subcommands.md#overview": {
      "direction": "code-is-truth",
      "governs": "framework/scripts/gnhf_guard.py",
      "doc_hash": "sha256:…",
      "code_hash": "sha256:…",
      "last_verdict": "in-sync",
      "blessed_at": "<git-sha>"
    }
  }
}
```

- Key = `<doc-path>#<doc_anchor>`, stable across content edits. **Schema
  follow-up (M2):** when a binding's `governs` globs multiple files, this key
  is not unique - each matched file is a distinct binding row. The lockfile key
  must incorporate the governed file (e.g. `<doc-path>#<doc_anchor>::<governed-file>`)
  so glob-expanded rows do not collide. M1's `plan` already disambiguates via a
  per-(binding, governed-file) `entry_id`.
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

### Success metrics (invariants from framework/docs/adr/0003)

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

Recorded in framework/docs/adr/0003 (explicit direction; anchored region+hash; Python;
safe-direction-only apply; no-semantic-KG-first).
