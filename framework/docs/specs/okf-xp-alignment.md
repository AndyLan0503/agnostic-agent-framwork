# OKF and XP alignment

## Analysis

### Problem / motivation

A design session surfaced two framings the repo already half-embodies but
never names, leaving alignment implicit and enforcement uneven.

1. **OKF (Open Knowledge Format).** The `framework/knowledge/` corpus is already
   OKF-shaped: markdown + YAML frontmatter, one fact per card, cross-linked,
   git-native (`framework/knowledge/README.md` card format; every card carries
   `id/title/tags/related/adr/confidence/sources/updated`). But nothing in
   the repo states this, and the frontmatter uses repo-local field names that
   diverge from OKF's reserved set (`type, title, description, resource, tags,
   timestamp`). The gap is documentation and, optionally, a field-name
   reconciliation - not a structural rebuild.

2. **XP enforcement.** The repo already encodes XP disciplines piecemeal:
   guardrail 2 "Behavior changes land with tests, written first. Prefer
   larger-scoped tests against real dependencies over narrow mocks"
   (AGENTS.md Guardrails) is test-first/TDD; `framework/roles/implementer.md` step 1
   "Work test-first"; guardrail 5 "Red is fixed now" is continuous
   integration discipline; `framework/roles/interrogator.md` "Unnecessary complexity -
   a simpler design that meets the same criteria" is YAGNI/simplest-thing;
   the implementer/interrogator split is enforced pairing ("the implementer
   never reviews their own change", AGENTS.md Roles). The XP name is never
   used and several practices (merciless refactoring, collective ownership,
   YAGNI as a guardrail) are aspirational prose with no enforcement row. Per
   the repo's own thesis (framework/docs/adr/0002: "a rule that exists only in prose is
   a wish"), unenforced XP claims are wishes.

The motivation now: naming both framings makes the repo legible to newcomers
and to agents, and the OKF standard (published 2026-06-12) gives the
knowledge corpus an external, citable spec to conform to.

### User stories

- **As a knowledge-card author (human or agent)**, I want the card format to
  state its relationship to OKF and use predictable field names, so I know
  which fields are the standard's and which are this repo's extensions.
- **As a newcomer reading AGENTS.md**, I want XP named explicitly and mapped
  to the guardrails and roles that enforce each practice, so I understand
  which disciplines are mechanically enforced versus merely encouraged.
- **As an implementer-role agent**, I want XP practices that apply to my work
  (test-first, YAGNI, refactoring, green-before-done) stated as checkable
  obligations in `framework/roles/implementer.md`, backed by a mechanism where one
  exists, so the discipline does not depend on my willpower.
- **As a security-reviewer / release-captain (read-only roles)**, I want any
  new XP "enforcement" claim to appear in the AGENTS.md enforcement map with
  a real mechanism, so I can audit that it is not a wish.
- **As a maintainer**, I want each new claim tied to a file path, so the
  drift reconciler (framework/docs/adr/0003) can eventually govern it.

### Acceptance criteria (Given/When/Then)

- **OKF naming.** Given the `framework/knowledge/` corpus, When a reader opens
  `framework/knowledge/README.md`, Then it states that the cards follow OKF (Open
  Knowledge Format, the standard published 2026-06-12), names OKF's reserved
  fields, and lists which repo fields are OKF-reserved versus repo
  extensions.
- **OKF conformance (only if in scope, see open questions).** Given a card,
  When its frontmatter is inspected, Then every OKF-reserved field it carries
  uses the OKF reserved name, and repo-only fields (`id, related, adr,
  confidence, sources, updated`) are documented as extensions - with no card
  losing existing information.
- **OKF card exists.** Given the knowledge base, When a reader greps for the
  OKF alignment fact, Then a card records it (with `sources` pointing at
  `framework/knowledge/README.md` and, if written, the OKF ADR) and appears in the
  `framework/knowledge/README.md` Index.
- **XP naming.** Given AGENTS.md, When a reader looks for XP, Then the
  Guardrails or Conventions section names XP and maps each adopted practice
  (test-first, CI/red-is-fixed, YAGNI, pairing via role split, collective
  ownership, refactoring) to the guardrail, role, or mechanism that carries
  it.
- **XP enforceability.** Given any XP practice presented as enforced, When
  the AGENTS.md enforcement map is checked, Then that practice has a row
  naming a mechanism that does not depend on agent cooperation; a practice
  with no such mechanism is labelled a convention, not a guardrail.
- **XP in the implementer role.** Given `framework/roles/implementer.md`, When an
  implementer-role agent reads it, Then the XP obligations that apply to
  implementation are stated as checkable steps, consistent with AGENTS.md and
  adding no new autonomy.
- **No regression.** Given the change, When `make test` runs, Then it stays
  green, and no shim file gains content beyond its pointer
  (framework/knowledge/shim-files-point-to-agents-md.md).

### In scope

- Naming the OKF alignment in `framework/knowledge/README.md` and recording it as a
  knowledge card in the Index.
- Naming XP and mapping its practices in AGENTS.md (Guardrails / Enforcement
  map / Roles / Conventions).
- Stating XP obligations as checkable steps in `framework/roles/implementer.md` within
  existing autonomy limits.
- Any OKF reserved-field adoption in the card format and existing cards
  (gated by open questions below), preserving all current information.

### Out of scope

- Adopting OKF's `resource` semantics or any external OKF tooling/validator
  beyond field naming.
- Building new automated XP enforcement code (test-first linters, refactoring
  detectors, coverage gates). This spec decides whether such mechanisms are
  warranted; building them is separate work.
- Changing the drift reconciler (framework/docs/adr/0003) or its schema; OKF/XP cards
  may later be governed by it but that binding is not built here.
- CI wiring, git hooks, or branch protection (the repository layer stays a
  `<fill in>` per framework/docs/adr/0002).
- Restructuring any card into multiple cards beyond what field-renaming
  requires.

### Constraints and invariants touched

- **Guardrail 2** (behavior changes land with tests, written first) - the XP
  test-first framing formalizes this guardrail; must not weaken it.
- **Guardrail 5** (red is fixed now) - the XP continuous-integration framing
  formalizes this; must not weaken it.
- **Guardrail 3** (agents never commit/push/merge/deploy on their own) - XP's
  "continuous integration" and "collective ownership" must not be read as
  license for autonomous commits or merges; the implementer role stays
  no-commit.
- **framework/docs/adr/0002** (limits enforced by construction, not prose) - any XP
  practice labelled "enforced" needs an enforcement-map row with a real
  mechanism; unmechanizable practices stay conventions. This is the primary
  constraint on the XP half.
- **framework/docs/adr/0001** (tool-neutral source of truth; shims are pointers) - all
  XP/OKF guidance lands in AGENTS.md / `framework/roles/` / `framework/knowledge/`, never in a
  harness shim (framework/knowledge/shim-files-point-to-agents-md.md).
- **framework/knowledge/README.md conventions** - one fact per card; the OKF card must
  be a single fact, and any field rename must keep `sources` pointing at code
  that proves the claim.
- **framework/docs/specs/README.md** - "A decision that is expensive to reverse gets
  promoted to an ADR"; the OKF field-rename question is exactly such a
  decision (see open questions).

### Open questions

1. **Does OKF alignment warrant its own ADR?** A field-name migration and an
   external-standard commitment are expensive to reverse (framework/docs/adr/README.md:
   "expensive to reverse - ... data contracts"), and the card frontmatter is
   a data contract the reconciler will consume. Recommendation to resolve in
   `## Spec`: yes for the *decision to conform to OKF and how to map fields*;
   the naming-only slice (README + card, no renames) could ship as a
   knowledge-card + README change without an ADR. Which slice is P0?
2. **Should the card format adopt OKF's reserved field names?** Three
   options: (a) rename to OKF names where they map (`title` already matches;
   `tags` already matches; add `type`, `description`, `timestamp`; keep
   `id/related/adr/confidence/sources/updated` as documented extensions),
   (b) document the mapping only and keep current names, (c) full rename
   including dropping/aliasing `updated`→`timestamp`. Migration cost: every
   card in `framework/knowledge/` (currently 3) plus `framework/knowledge/README.md` plus any
   `reconcile` frontmatter interaction (gnhf-safe-subcommands.md already
   carries a `reconcile:` block - renames must not collide with it). What is
   OKF's required `type` vocabulary, and does every card have a natural
   `type`?
3. **Is `resource` (OKF-reserved) meaningful here, or omitted?** The repo's
   `sources` field is close but not identical; decide whether to map
   `sources`→`resource`, keep both, or leave `resource` unused.
4. **XP: documentation-only or new mechanisms?** Which practices are
   mechanizable versus aspirational?
   - *Mechanizable now (already have a mechanism):* test-first (guardrail 2 +
     PR template "How tested"), continuous integration / green-before-merge
     (guardrail 5 + `make test` gate), pairing (implementer≠reviewer role
     split, already structural). These become named XP rows citing existing
     mechanisms - no new code.
   - *Aspirational (no cooperation-free mechanism today):* merciless
     refactoring, YAGNI/simplest-thing (partially caught by the interrogator's
     "unnecessary complexity" pass, but that is a review, not a gate),
     collective ownership. Should these be labelled conventions, or is a new
     mechanism (e.g. a reconciler-style check, a required interrogator
     finding) warranted? Per framework/docs/adr/0002 they cannot be called "guardrails"
     without one.
5. **Does the XP framing change any guardrail wording, or only add a
   mapping?** Preference is additive (a new "XP disciplines" subsection +
   enforcement-map rows) to avoid destabilizing guardrail text that other
   artifacts cite by number.
6. **Scope of the OKF card's `sources`/proof** - once field names change, the
   card describing OKF alignment must cite the conformed cards; sequencing
   (rename first, then card, or card first) is a product-manager call.

## Spec

### Goal and non-goals

**Goal.** Make the repo's two implicit framings explicit and honest, and make
the two frontmatter formats one:
1. Conform the knowledge-card format to OKF (Open Knowledge Format), doing a
   FULL field rename across the format doc and every card, with no information
   loss. The OKF conformance decision and its exact field-mapping contract are
   recorded in EXISTING documents - `framework/knowledge/README.md` (the card-format
   authority) plus a naming note in AGENTS.md Conventions plus the new OKF
   card - NOT a new ADR (Change 1: the human directed no new ADR).
2. Unify the two frontmatter formats: declare the reconciler's `reconcile:`
   block an official OKF *extension* field so one frontmatter format serves the
   whole repo - a doc can be simultaneously an OKF document and a
   reconcile-governed one - and drift-govern each knowledge card by binding its
   claim to its `sources` (Change 2). This RELAXES the earlier invariants "no
   file under `framework/scripts/reconcile/` changed" and "`reconcile:` block
   byte-unchanged": `framework/scripts/reconcile` changes and card `reconcile:` bindings
   are now IN SCOPE.
3. Name Extreme Programming in AGENTS.md as an additive subsection, add
   enforcement-map rows only for XP practices that already have a
   cooperation-free mechanism, and restate the implementer's XP obligations as
   checkable steps - all additive, no new autonomy, no new XP enforcement code.

**Non-goals** (parked, from the Analysis and the human's two decisions):
- A new ADR. The OKF conformance decision and field-mapping table are recorded
  in `framework/knowledge/README.md`, AGENTS.md Conventions and the OKF card (Change 1),
  not in ADR-0004; ADR-0004 is dropped entirely.
- Adopting OKF `resource` semantics or any OKF tooling/validator. `resource`
  stays optional and unused unless a card has a natural URL for the resource
  it describes. `sources` stays a repo extension, NOT remapped to `resource`.
- New XP enforcement code (test-first linters, refactoring detectors, coverage
  gates, required-interrogator-finding checks). Explicitly out of scope.
  Practices lacking a mechanism today are labelled CONVENTIONS.
- Rewording the existing numbered guardrails. Other artifacts cite them by
  number; the XP framing is purely additive (resolving open question 5).
- Any reconciler behavior change beyond what unification requires. In scope:
  verifying/extending `framework/scripts/reconcile/frontmatter.py` to parse OKF-format
  cards cleanly, one new reconcile fixture + test, and card `reconcile:`
  bindings. Out of scope: the reconciler's `direction`/state schema, lockfile
  writer, `apply`, judge, or CI wiring (framework/docs/adr/0003 M2+).
- CI, git hooks, branch protection (repository layer stays `<fill in>`).
- Restructuring any card into multiple cards beyond what the rename requires.

### Prioritized requirements

**P0 - the shippable slice (all of the below ship together in one pass):**

*OKF half (full rename, decision recorded in existing docs - NO ADR - no
information loss):*

- **P0-1. Record the OKF decision + field mapping in existing docs (no ADR).**
  Change 1 drops ADR-0004 entirely. Record the same content in the documents
  that already exist:
  - `framework/knowledge/README.md` (the card-format authority) gets the OKF subsection
    AND the field-mapping/rationale table (P0-2).
  - `AGENTS.md` Conventions gets a one-line note naming OKF as the
    knowledge-card format (folded into P0-8 with the XP work, or done here -
    either order is green).
  - the new OKF card records the alignment fact (P0-3).
  There is no `framework/docs/adr/0004-*.md` file, no `framework/docs/adr/README.md` row for it,
  and no citation of ADR-0004 anywhere. The `adr:` extension field on cards is
  unaffected - existing cards keep their real ADR references (0001, 0002); the
  OKF card carries no `adr:` (its decision is not ADR-backed).

  Field mapping (the exact contract `framework/knowledge/README.md` records):

  | Current field | OKF outcome | Notes |
  |---|---|---|
  | `title` | `title` (OKF-reserved) | unchanged |
  | `tags` | `tags` (OKF-reserved) | unchanged |
  | `updated` | `timestamp` (OKF-reserved) | renamed; same `YYYY-MM-DD` value |
  | - (new) | `type` (OKF-REQUIRED) | added; vocabulary below |
  | - (new) | `description` (OKF-reserved) | added; one-line summary |
  | `id` | `id` (extension) | documented repo extension |
  | `related` | `related` (extension) | documented repo extension |
  | `adr` | `adr` (extension) | documented repo extension |
  | `confidence` | `confidence` (extension) | documented repo extension |
  | `sources` | `sources` (extension) | proof-of-claim globs; NOT `resource` |
  | `reconcile` | `reconcile` (extension) | reconciler binding block; official OKF extension (P0-5) |
  | - | `resource` (OKF-reserved) | left optional/unused |

  Rationale the doc must state: only `type` is OKF-REQUIRED; OKF permits
  extension fields, so every repo field (including `reconcile`) survives as a
  documented extension; `sources` is NOT remapped to `resource` (they differ:
  `resource` is the canonical link to the described resource, `sources` are
  proof-of-claim file globs); `resource` stays optional/unused.

  `type` vocabulary (small, closed set the implementer applies per card):
  `convention` and `mechanism`. Assign each existing card its natural type:
  - `shim-files-point-to-agents-md` -> `convention`
  - `handoffs-are-files` -> `convention`
  - `gnhf-safe-subcommands` -> `mechanism`
  - the new OKF card (P0-3) -> `convention`

  If the implementer finds a card that fits neither, stop and flag rather than
  inventing a third type (keeps the vocabulary checkable).

- **P0-2. Card format doc + OKF subsection (`framework/knowledge/README.md`).** Rewrite
  the "Card format" fenced example to use OKF names: `type` first (REQUIRED),
  then `title`, `description`, `tags`, `timestamp`, then the extensions
  (`id, related, adr, confidence, sources`, and `reconcile` where present). Add
  an OKF subsection stating the cards follow OKF (Open Knowledge Format,
  published 2026-06-12), naming OKF's reserved set
  (`type, title, description, resource, tags, timestamp`), marking `type` as
  the only required field, carrying the field-mapping table and rationale from
  P0-1, and declaring `reconcile:` an official OKF extension field (P0-5) so
  one frontmatter format serves both the knowledge base and the reconciler.
  Note `resource` is reserved-but-unused. This subsection - not an ADR - is the
  authority the OKF card cites.

- **P0-3. Migrate every card + add the OKF card.** Apply the rename to all
  three existing cards (`updated`->`timestamp`; add `type` and `description`).
  Preserve every existing scalar field value verbatim (no information loss).
  The `reconcile:` block in `gnhf-safe-subcommands.md` is now IN SCOPE (Change
  2): align it to the drift-govern pattern in P0-6, but change nothing else in
  it beyond that alignment. Add one new card
  `framework/knowledge/knowledge-cards-follow-okf.md` (`type: convention`) recording the
  OKF-alignment fact, with `sources` pointing at `framework/knowledge/README.md` (the
  authority - no ADR to cite), and add it to the `framework/knowledge/README.md` Index.

- **P0-4. Conformance test (guardrail 2 - behavior lands with tests).** Add a
  stdlib-only `framework/scripts/test_knowledge_cards.py` (unittest, discovered by
  `make test`) that, for every `framework/knowledge/*.md`:
  1. the file has a parseable `---`-delimited YAML frontmatter block;
  2. its frontmatter carries a `type` field (OKF-REQUIRED) whose value is in
     the closed vocabulary `{convention, mechanism}`;
  3. no card still carries the retired `updated` key (rename completeness);
  4. every card carrying a `reconcile:` block parses cleanly via
     `reconcile.frontmatter.parse_frontmatter` (an OKF card and a
     reconcile-governed card are the same file - this guards unification).

  Write these as failing tests first, then make the migration pass them. Keep
  it minimal: no third-party YAML dependency - parse the frontmatter block with
  stdlib only (the fields under test are flat scalars/lists). This test is the
  cooperation-free mechanism that keeps future cards OKF-conformant.

*Unification + drift-govern (Change 2 - `framework/scripts/reconcile` now in scope):*

- **P0-5. Unify the frontmatter (`reconcile:` is an OKF extension field).**
  Declare `reconcile:` an official OKF extension field so one frontmatter
  format serves the whole repo: a doc can be simultaneously an OKF document
  (scalar OKF fields + repo scalar extensions) and a reconcile-governed one
  (the nested `reconcile:` block). Document this in BOTH `framework/knowledge/README.md`
  (the OKF subsection, P0-2) and `framework/docs/specs/reconcile.md` (a note that the
  `reconcile:` block is one field of an OKF-format document, coexisting with
  OKF scalars). Then make the parser honest about it:
  - Verify `framework/scripts/reconcile/frontmatter.py` cleanly parses OKF-format cards -
    OKF scalar fields (`type, title, description, tags, timestamp, id, related,
    adr, confidence, sources`) coexisting with a `reconcile:` block. The
    current parser scans for the top-level `reconcile:` key and skips sibling
    scalars before it, so `gnhf-safe-subcommands.md` (scalars THEN `reconcile:`)
    already parses; confirm this and extend the parser only if a real card
    exposes a gap (e.g. sibling scalars appearing AFTER the `reconcile:` block,
    which the current `_indent(line) <= base_indent: break` already handles by
    ending the block). Any parser change lands with a test.
  - Add a reconcile fixture that is a full OKF-conformant card (all OKF scalars
    + extensions + a `reconcile:` block) and a `test_frontmatter.py` case
    asserting `parse_frontmatter` returns the right `direction` and `bindings`
    from it, ignoring the OKF scalars. This is the regression proving the two
    formats are one.

- **P0-6. Drift-govern the knowledge cards.** Add a `reconcile:` binding to the
  sourced knowledge cards so each card's claim is drift-checked against its
  `sources`. Uniform pattern:
  - `direction: code-is-truth` - a card describes the repo/code; if the sourced
    file moves, the card may have drifted (never the reverse).
  - `governs` = the card's `sources` file(s). When a card has multiple sources,
    add one binding per source (the reconciler keys per governed file,
    framework/docs/specs/reconcile.md M2 note).
  - `doc_anchor` = the card body. Prefer a fenced region
    (`<!-- reconcile:<anchor>:start/end -->`) around the load-bearing claim;
    absent fences degrade to whole-doc (framework/docs/specs/reconcile.md), which is
    acceptable for short cards.
  - Align the existing `gnhf-safe-subcommands.md` block to this same pattern
    (it already has `direction: code-is-truth` + a fenced `criterion` binding;
    keep it, it is the template).

  **Which cards get a binding (state the decision):** EVERY sourced card gets a
  binding, whether its `sources` are Python or docs. For cards whose `sources`
  are docs (e.g. `handoffs-are-files` -> `AGENTS.md`,
  `framework/docs/adr/0001-*.md`; `shim-files-point-to-agents-md` -> the shim files) the
  reconciler simply hash-gates / degrades to whole-file (framework/docs/specs/reconcile.md:
  "non-Python file ... degrades to the whole file"), which is fine - it still
  catches gross drift. The new OKF card's `sources` is `framework/knowledge/README.md`
  (a doc), so it too gets a `code-is-truth` whole-file binding. No card is left
  ungoverned; there is no code-vs-doc carve-out.

  This must not break the reconcile subpackage tests: bindings on real cards
  are parsed by the same `frontmatter.py` the fixtures exercise; the new fixture
  (P0-5) is the direct regression.

*XP half (name + map, additive, no new code):*

- **P0-7. Enforcement-map rows (only the three with a real mechanism).** Add
  exactly three rows to the AGENTS.md Enforcement map, each citing an EXISTING
  mechanism (no new code):
  - test-first -> guardrail 2 + PR template "How tested" / test-first checkbox
  - continuous integration -> guardrail 5 + `make test` gate (local, and CI
    `<fill in>` per framework/docs/adr/0002)
  - pairing -> implementer != reviewer role split (reviewer roles read-only)

  Do not add rows for refactoring / collective ownership / YAGNI: with no
  mechanism, a row would itself be a wish (framework/docs/adr/0002).

- **P0-8. Name XP in AGENTS.md + OKF Conventions note, additively.** Add a new
  subsection (a dedicated "Extreme Programming" subsection under
  Roles-and-workflow, or in Conventions) that names XP and maps each adopted
  practice to the guardrail/role/mechanism that already carries it. Do NOT edit
  the text of guardrails 1-6. Classify:
  - test-first -> guardrail 2 (+ PR template "How tested" / test-first
    checkbox)
  - continuous integration / green-before-merge -> guardrail 5 (+ `make test`
    gate)
  - pairing -> the implementer != reviewer role split (structural)
  - merciless refactoring, collective ownership, YAGNI-as-gate -> labelled
    CONVENTIONS (no cooperation-free mechanism today, per framework/docs/adr/0002); name
    them but do not call them guardrails or enforcement.

  In the same edit, add the one-line OKF note to AGENTS.md Conventions from
  P0-1: knowledge cards follow OKF (Open Knowledge Format); the format
  authority is `framework/knowledge/README.md`.

- **P0-9. Implementer XP obligations (`framework/roles/implementer.md`).** Restate the
  XP obligations that apply to implementation as checkable steps, adding no new
  autonomy (implementer stays no-commit, read-write within the spec). Cover:
  test-first (already step 1 - keep, frame as XP); green-before-done (already
  step 2); YAGNI / simplest-thing-that-works as a self-check; refactor-with-
  green-tests as permitted-but-bounded. Each step phrased so a reviewer can
  check it was followed. Do not grant commit/push or scope-expansion rights.

**P1 - deferred (not in this pass):** any new XP enforcement mechanism;
`resource` population for cards that later gain a natural URL; lockfile
seeding / `sync` / `apply` for the new card bindings (framework/docs/specs/reconcile.md
M2+ - this pass only adds the bindings and proves they parse, it does not run
the reconciler's later milestones).

### Success metrics

- `make test` green after the change, including the new
  `framework/scripts/test_knowledge_cards.py` AND the existing reconcile subpackage tests
  (none broken by the parser/fixture work).
- Zero information loss: a diff of each card before/after shows only additions
  (`type`, `description`, a `reconcile:` binding) and the
  `updated`->`timestamp` key rename - no scalar value dropped.
- Every `framework/knowledge/*.md` carries a `type` in `{convention, mechanism}`; no card
  carries `updated`. (Enforced by P0-4, not just observed.)
- `framework/knowledge/README.md` names OKF, its reserved set, the required field, the
  reserved-vs-extension split, the field-mapping table and rationale, and
  declares `reconcile:` an OKF extension. It cites NO ADR-0004 (recorded here,
  not in an ADR).
- No `framework/docs/adr/0004-*.md` file exists; no `framework/docs/adr/README.md` row for it; no
  string "ADR-0004" anywhere in the tree.
- AGENTS.md Conventions names OKF as the knowledge-card format.
- **Unification:** `reconcile.frontmatter.parse_frontmatter` returns the
  correct `direction` and `bindings` for a full OKF-conformant card (proven by
  the new reconcile fixture + test); the same function parses every real card
  carrying a `reconcile:` block.
- **Drift-govern:** every sourced knowledge card (including the new OKF card)
  carries a `code-is-truth` `reconcile:` binding whose `governs` is its
  `sources`; `gnhf-safe-subcommands.md`'s block follows the same pattern.
- `framework/docs/specs/reconcile.md` notes that `reconcile:` is one field of an
  OKF-format document.
- AGENTS.md names XP; exactly three XP enforcement rows, each with an existing
  mechanism; refactoring/collective-ownership/YAGNI present as CONVENTIONS with
  no enforcement claim.
- No guardrail 1-6 wording changed (git diff of the numbered list is empty).
- No shim file gains content beyond its pointer
  (framework/knowledge/shim-files-point-to-agents-md.md).

### Rollout and risk

**Migration order** (also the sequencing below): format doc + decision
recorded in existing docs first (establishes the contract, no ADR), then the
conformance test + card migration + `reconcile:` bindings (enforces it), then
the reconcile frontmatter unification + fixture/test, then the additive
AGENTS.md XP subsection + rows + OKF note, then implementer.md. Each step
leaves `make test` green.

**The reconcile-block risk (primary), now managed by unification not
avoidance.** `gnhf-safe-subcommands.md` carries a `reconcile:` frontmatter
block (framework/docs/adr/0003) that `framework/scripts/reconcile/frontmatter.py` parses as its own
nested namespace; it scans for the top-level `reconcile:` key and ignores
sibling scalars before it. Change 2 makes this coexistence official: the OKF
scalar rename (`updated`->`timestamp`, add `type`, `description`) touches only
sibling scalars, and every card now carries a `reconcile:` block by design.
Mitigations: (a) the parser is verified/extended to parse OKF-format cards, with
a new full-card fixture as the regression (P0-5); (b) P0-4 item 4 asserts every
card's `reconcile:` block parses via `reconcile.frontmatter`; (c) the existing
reconcile subpackage tests stay green (success metric). Blast radius if a parser
change regresses: caught by the reconcile subpackage's own tests and the new
fixture before merge.

**Blast radius.** Contained but slightly wider than before: no new ADR; edits
to `framework/knowledge/README.md` (format + OKF subsection), 3 migrated + drift-governed
cards, 1 new OKF card, 1 new `framework/scripts/test_knowledge_cards.py`; a note in
`framework/docs/specs/reconcile.md`; a possible small change to
`framework/scripts/reconcile/frontmatter.py` plus one new fixture and one new
`test_frontmatter.py` case; additive edits to AGENTS.md (XP subsection, 3
enforcement rows, OKF Conventions note) and `framework/roles/implementer.md`. No change to
`framework/scripts/gnhf*` or the reconciler's runtime behavior beyond frontmatter parsing.
The `type` vocabulary is closed (`convention`/`mechanism`), so future cards get a
checkable constraint rather than open-ended drift.

**Rollback.** Revert the single PR. The rename and bindings are mechanical;
because the decision lives in `framework/knowledge/README.md` (not an append-only ADR),
reverting the PR fully unwinds it with no ADR to mark Superseded. No
data-migration to unwind beyond the card frontmatter itself.

**Risks carried from punted open questions:**
- OQ2 `type` vocabulary: chosen minimal (`convention`/`mechanism`). Risk: a
  future card fits neither; mitigated by instructing the implementer to STOP
  and flag rather than silently add a third type, so the vocabulary stays a
  checked contract that grows only by explicit decision.
- OQ3 `resource`: deliberately left unused; risk is only a future card wanting
  it, which is a cheap additive follow-up (P1), not a reversal.
- Parser change risk (new, Change 2): extending `frontmatter.py` could regress
  the reconciler. Mitigated by keeping the existing subpackage tests green and
  landing any change with the new full-card fixture + test; if the current
  parser already handles OKF-format cards (likely - it skips sibling scalars),
  the "change" is verification only, and the fixture still guards it.
- Whole-file bindings on doc-sourced cards degrade coarsely (no symbol-level
  scoping for non-Python `sources`). Accepted: coarse drift-catching beats
  none, and matches framework/docs/specs/reconcile.md's stated degrade-to-whole-file
  behavior; refining to anchored regions is a later, additive follow-up.

### Decisions needing an ADR

**None.** The human directed no new ADR (Change 1). Both decisions are recorded
in existing documents:

- **OKF conformance** (the field-mapping table, `type` as the sole required
  field with the `{convention, mechanism}` vocabulary, repo fields incl.
  `reconcile` retained as documented extensions, `sources` NOT remapped to
  `resource`, `resource` left optional/unused) is recorded in
  `framework/knowledge/README.md` (the card-format authority), with a naming note in
  AGENTS.md Conventions and the alignment fact in the new OKF card - NOT in an
  ADR. Although this is a data contract the reconciler consumes, the human
  scoped it to the format authority document; `framework/knowledge/README.md` is the
  single citable source and the conformance test (P0-4) is its enforcement.

- **Unification of the two frontmatter formats** (`reconcile:` as an OKF
  extension field; every card drift-governed) is recorded in
  `framework/knowledge/README.md` and `framework/docs/specs/reconcile.md`, enforced by the parser +
  the new fixture/test - not an ADR.

- **XP framing** is additive documentation mapping existing mechanisms; it
  changes no data contract and reverts by a revert. Recorded in AGENTS.md and
  `framework/roles/implementer.md`, not an ADR. (Resolves open question 5: additive
  only.)

### Sequencing

One implementer can wear the hat throughout, but the work is ordered so each
step is independently `make test` green and reviewable. The implementer never
reviews their own change (interrogator + security-reviewer follow, read-only).

1. **Format + decision docs first (no ADR).** Rewrite `framework/knowledge/README.md`
   card format + OKF subsection carrying the field-mapping table, rationale,
   and the `reconcile:`-is-an-OKF-extension declaration (P0-1, P0-2, and the
   P0-5 documentation half). No card touched yet. Confirm no ADR-0004 is
   created and nothing cites it.
2. **Conformance test + card migration + reconcile bindings.** Add
   `framework/scripts/test_knowledge_cards.py` (P0-4) as failing tests, then migrate all
   three cards (`updated`->`timestamp`, add `type`/`description`) and add the
   new OKF card (P0-3), and add each card's `code-is-truth` `reconcile:`
   binding, aligning `gnhf-safe-subcommands.md` to the pattern (P0-6). Tests
   pass; `make test` green.
3. **Reconcile frontmatter unification + reconcile test.** Verify/extend
   `framework/scripts/reconcile/frontmatter.py` to parse OKF-format cards, add the
   full-OKF-card fixture and the `test_frontmatter.py` case, and add the note
   to `framework/docs/specs/reconcile.md` (P0-5 code half). Existing reconcile subpackage
   tests stay green.
4. **AGENTS.md XP subsection + 3 enforcement rows + OKF note.** Add the additive
   XP subsection (P0-8), the three enforcement-map rows (P0-7), and the OKF
   Conventions note (P0-1/P0-8). Confirm guardrails 1-6 wording is untouched
   (empty diff on the numbered list).
5. **Implementer obligations.** Restate XP obligations as checkable steps in
   `framework/roles/implementer.md` (P0-9), adding no autonomy.

Each step ends with `make test` green; the PR carries a single gitmoji and
fills the PR template's "How tested" with the real `make test` output.
