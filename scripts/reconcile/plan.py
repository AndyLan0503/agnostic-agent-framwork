"""Read-only drift `plan` (docs/adr/0003, M1).

Tier 0 (git-diff hash-gate) -> Tier 1 (structural blast-radius) -> optional
judge on the frontier. Writes nothing: no lockfile, sync, apply, or CI
wiring (those are M2+). With no judge, frontier bindings are `needs-judge`
and zero tokens are spent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import docstate
from .docstate import classify
from .frontmatter import Direction, parse_frontmatter
from .gitdiff import ChangedSet, changed_set
from .graph import DocNode, build_graph, frontier
from .judge import Judge, Verdict, VerdictKind, build_frontier
from .regions import (
    Region, hash_span, resolve_code_region, resolve_doc_region,
    resolve_governed_files,
)


@dataclass
class PlanEntry:
    entry_id: str                # unique per (binding, governed-file)
    key: str                     # <doc-path>#<doc_anchor>
    direction: str | None
    governs: str
    doc_hash: str | None
    code_hash: str | None
    verdict: str
    on_frontier: bool
    rationale: str = ""
    error: str | None = None


@dataclass
class Plan:
    base: str
    diff_available: bool
    judged: bool
    entries: list[PlanEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "base": self.base,
            "diff_available": self.diff_available,
            "judged": self.judged,
            "entries": [asdict(e) for e in self.entries],
        }


_VENDORED = {"node_modules", "vendor", "__pycache__", "site-packages",
             "dist", "build", "target", "venv"}


def _pruned_walk(root: Path, suffix: str) -> list[Path]:
    """rglob for `suffix`, skipping hidden (leading `.`) and vendored dirs."""
    out: list[Path] = []
    stack = [root]
    while stack:
        for entry in sorted(stack.pop().iterdir()):
            if entry.is_dir():
                if entry.name.startswith(".") or entry.name in _VENDORED:
                    continue
                stack.append(entry)
            elif entry.suffix == suffix:
                out.append(entry.relative_to(root))
    return sorted(out)


def _managed_docs(root: Path) -> list[Path]:
    return _pruned_walk(root, ".md")


@dataclass
class _Resolved:
    entry_id: str
    key: str
    direction: Direction
    governs: str
    doc_region: Region
    code_region: Region
    binding: object
    doc_hash: str
    code_hash: str


@dataclass
class Resolution:
    """Every managed binding resolved to hashed doc/code regions, plus the
    error entries and graph inputs. Shared by `plan`, `sync` and `apply`."""
    resolved: list[_Resolved] = field(default_factory=list)
    errors: list[PlanEntry] = field(default_factory=list)
    doc_nodes: list[DocNode] = field(default_factory=list)
    py_files: set[Path] = field(default_factory=set)


def resolve_bindings(root: Path) -> Resolution:
    """Resolve every managed doc's bindings without any git/judge/lockfile
    signal - pure region resolution and hashing (read-only)."""
    root = Path(root).resolve()
    out = Resolution()
    for doc_path in _managed_docs(root):
        text = (root / doc_path).read_text(encoding="utf-8")
        managed = parse_frontmatter(text)
        if managed is None:
            continue  # unmanaged doc -> ignored
        if managed.error:
            out.errors.append(PlanEntry(
                entry_id=f"{doc_path}#<error>",
                key=f"{doc_path}#<error>", direction=None, governs="",
                doc_hash=None, code_hash=None,
                verdict="error", on_frontier=False, error=managed.error))
            continue
        for binding in managed.bindings:
            doc_region = resolve_doc_region(root, doc_path, binding)
            for gov in resolve_governed_files(root, binding.governs):
                key = f"{doc_path}#{binding.doc_anchor}"
                if gov.error is not None:
                    out.errors.append(PlanEntry(
                        entry_id=f"{key}::{binding.governs}",
                        key=key, direction=managed.direction.value,
                        governs=binding.governs, doc_hash=None,
                        code_hash=None, verdict="error", on_frontier=False,
                        error=gov.error))
                    continue
                gov_file = gov.path
                code_region = resolve_code_region(
                    root, gov_file, binding.code_anchor)
                # Fold the governed file into the identity so a glob matching
                # multiple files yields distinct, non-colliding nodes/entries.
                entry_id = f"{key}::{gov_file}"
                out.resolved.append(_Resolved(
                    entry_id=entry_id, key=key, direction=managed.direction,
                    governs=str(gov_file), doc_region=doc_region,
                    code_region=code_region, binding=binding,
                    doc_hash=_safe_hash(root, doc_region),
                    code_hash=_safe_hash(root, code_region)))
                out.doc_nodes.append(DocNode(
                    key=key, region=code_region, node_id=entry_id))
                if (root / gov_file).suffix == ".py":
                    out.py_files.add(gov_file)
    return out


def plan(root: Path, base: str = "HEAD", judge: Judge | None = None,
         depth: int = 2) -> Plan:
    root = Path(root).resolve()
    changed = changed_set(root, base)
    recorded = docstate.load(root)
    res = resolve_bindings(root)
    entries: list[PlanEntry] = list(res.errors)
    resolved = res.resolved
    doc_nodes = res.doc_nodes
    py_files = res.py_files

    graph = build_graph(root, doc_nodes, py_files | _all_py(root))
    changed_code = _changed_code_keys(graph, changed)
    frontier_keys = frontier(graph, changed_code, depth)

    for r in resolved:
        doc_changed = changed.overlaps(
            r.doc_region.path, r.doc_region.start, r.doc_region.end)
        code_changed = changed.overlaps(
            r.code_region.path, r.code_region.start, r.code_region.end)
        # No diff signal (not a repo / unknown ref) cannot prove unchanged, so
        # every binding is on the frontier (widen, never narrow).
        git_frontier = (not changed.available or r.entry_id in frontier_keys
                        or code_changed or doc_changed)

        # Recorded state (M2): drift is recorded-vs-actual hashes. When a
        # binding is blessed, its hashes are the authoritative signal; the
        # git-diff/blast-radius frontier is unioned in so transitive change
        # still surfaces before the first `sync` (precision handled by judge).
        record = recorded.get(r.entry_id) if recorded else None
        structural = None
        if record is not None:
            structural = classify(record.doc_hash != r.doc_hash,
                                  record.code_hash != r.code_hash)
        on_frontier = git_frontier or (
            structural is not None and structural is not VerdictKind.IN_SYNC)

        if not on_frontier:
            entries.append(_entry(r, VerdictKind.IN_SYNC, on_frontier=False))
            continue

        if judge is not None:
            item = build_frontier(root, r.key, r.direction, r.binding,
                                  r.doc_region, r.code_region)
            verdict = judge(item)
            entries.append(_entry(r, verdict.verdict, on_frontier=True,
                                  rationale=verdict.rationale))
            continue

        # No judge: emit the free directional verdict when recorded hashes
        # pin it down, else `needs-judge`.
        free = (structural if structural and structural is not
                VerdictKind.IN_SYNC else VerdictKind.NEEDS_JUDGE)
        entries.append(_entry(r, free, on_frontier=True))

    entries.sort(key=lambda e: e.entry_id)
    return Plan(base=base, diff_available=changed.available,
                judged=judge is not None, entries=entries)


def _entry(r: _Resolved, verdict: VerdictKind, on_frontier: bool,
           rationale: str = "") -> PlanEntry:
    return PlanEntry(
        entry_id=r.entry_id, key=r.key, direction=r.direction.value,
        governs=r.governs, doc_hash=r.doc_hash, code_hash=r.code_hash,
        verdict=verdict.value, on_frontier=on_frontier, rationale=rationale)


def _safe_hash(root: Path, region: Region) -> str | None:
    try:
        return hash_span(region.text(root))
    except (OSError, UnicodeDecodeError):
        return None


def _all_py(root: Path) -> set[Path]:
    return set(_pruned_walk(root, ".py"))


def _changed_code_keys(graph, changed: ChangedSet) -> set[str]:
    keys: set[str] = set()
    for key, node in graph.code.items():
        if changed.overlaps(Path(node.path), node.lineno, node.end_lineno):
            keys.add(key)
    return keys
