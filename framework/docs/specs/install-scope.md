# Install scope: framework-dev artifacts stay out of targets

## Analysis

- **Problem** - `framework/scripts/adopt.py` walks the filesystem, so it ships
  this repo's own development artifacts into targets: framework ADRs
  0001-0003, the framework's own feature specs, `knowform.lock`, and any
  untracked local file (e.g. a gitignored PDF present in a local checkout but
  absent from a clone - the two install paths disagree). Shipped files also
  reference things that then dangle in the target: the Makefile `adopt`
  target (its script is excluded), `framework/docs/adr/000X` citations, and
  knowform bindings governing `framework/docs/adr/0001-*` and
  `framework/scripts/adopt.py`.
- **Ownership test** - a file ships only if the target owns or uses it. The
  framework's own instance of a target-owned artifact (decision-log entries,
  feature specs, the lockfile) stays framework-side.
- **Acceptance criteria**
  - Given a local checkout with untracked files, When adoption runs, Then the
    installed set equals the set a fresh clone would install (enumeration
    from `git ls-files`, not the filesystem).
  - Given a freshly adopted target, Then it contains no framework ADR beyond
    `0000-template.md` and `README.md`, no spec beyond
    `framework/docs/specs/README.md`, no `knowform.lock`, and no `adopt`
    Make target.
  - Given the shipped file set, Then no file references a framework ADR in
    any form (path, `framework ADR-NNNN`, numbered link): rationale for
    framework decisions stays upstream, carried inline in a clause where a
    shipped rule needs its why. Dev-side traceability inverts: each ADR
    lists the shipped files it governs.
  - Given a future ADR or spec added to this repo, Then it is excluded
    structurally (pattern match), with no list to maintain.
- **In scope** - adopt.py enumeration + exclusions, Makefile, citation sweep
  across shipped files, knowledge-card frontmatter, adopt-framework skill
  binding, README adoption instructions.
- **Out of scope** - committed `.gitignore` content, untracking
  `knowform.lock`, CONTRIBUTING.md voice.
- **Guardrails touched** - 2 (test-first); the structural-exclusion approach
  follows framework ADR-0002 (limits by construction, not by list).

## Spec

- **Goal** - the installed set is product only, and identical across the
  local-path and remote-clone install routes.
- **Non-goals** - changing what the product mechanisms do; any behavior
  change in gnhf, reconcile, or the pipeline.
- **P0 slice** (all of):
  1. HEAD is the single source of both the file set and the file content:
     `scaffold_files()` enumerates `git ls-tree -r HEAD` (regular blobs
     only, so symlinks and gitlinks never ship) and `adopt()` reads bytes
     via `git show HEAD:<path>`. Uncommitted changes never ship; the local
     and clone routes install identical bytes whenever HEADs match. Clear
     error when the root is not itself a git repo (`rev-parse
     --show-toplevel` must equal the root). Exclusions, structural where
     possible: existing ownership ones, plus `knowform.lock`,
     `framework/docs/adr/NNNN-*.md` except `0000-template.md`, and
     `framework/docs/specs/*` except `README.md`. Re-adoption extends the
     three-way logic to deletions: candidates come from the manifest
     recorded in `.framework-version` (base-tree fallback for pre-manifest,
     SHA-only targets); a candidate matching its base content is removed
     (empty dirs pruned); a customized one is kept and reported orphaned;
     no base SHA, no deletions. Tests first in `test_adopt.py` (fixture repos need
     `git init` + commit).
  2. Remove the `adopt` target from the Makefile; README.md documents
     `python3 framework/scripts/adopt.py /path/to/target` instead.
  3. Citation removal in shipped files: framework-ADR citations are deleted
     (or replaced by a one-clause inline rationale); ADRs 0001-0003 gain a
     `## Governs` section as the reverse index; the broadened sweep test
     bans any numbered-ADR reference in shipped files so future leaks fail
     `make test`. References to the `framework/docs/adr/` directory as the
     target's own decision log stay as paths.
  4. Knowledge cards: drop `adr:` frontmatter entries and ADR paths from
     `sources:`; remove the `handoffs-are-files` binding governing
     `framework/docs/adr/0001-*`; cite framework ADRs in prose instead.
  5. `framework/skills/adopt-framework/SKILL.md`: remove the knowform binding
     governing `framework/scripts/adopt.py`.
- **Success metric** - a test asserts the excluded artifacts are absent from
  `scaffold_files()` output and that install from a dirty checkout matches
  install from a clean clone; a sweep test asserts no shipped markdown cites
  a non-shipped `framework/docs/adr/` path.
- **Rollout / risk** - single PR. Doc edits will stale `knowform.lock`
  hashes; refresh via the knowform CLI if available, otherwise note the
  drift in the PR (reconcile is non-blocking per framework ADR-0003).
- **Sequencing** - one implementer.
