"""Read-only drift `plan` (docs/adr/0003, M1).

Tier 0 (git-diff hash-gate) -> Tier 1 (structural blast-radius) -> optional
judge on the frontier. Writes nothing: no lockfile, sync, apply, or CI
wiring (those are M2+). With no judge, frontier bindings are `needs-judge`
and zero tokens are spent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

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


def _managed_docs(root: Path) -> list[Path]:
    return [p.relative_to(root) for p in sorted(root.rglob("*.md"))]


@dataclass
class _Resolved:
    key: str
    direction: Direction
    governs: str
    doc_region: Region
    code_region: Region
    binding: object
    doc_hash: str
    code_hash: str


def plan(root: Path, base: str = "HEAD", judge: Judge | None = None,
         depth: int = 2) -> Plan:
    root = Path(root).resolve()
    changed = changed_set(root, base)
    entries: list[PlanEntry] = []
    resolved: list[_Resolved] = []
    doc_nodes: list[DocNode] = []
    py_files: set[Path] = set()

    for doc_path in _managed_docs(root):
        text = (root / doc_path).read_text(encoding="utf-8")
        managed = parse_frontmatter(text)
        if managed is None:
            continue  # unmanaged doc -> ignored
        if managed.error:
            entries.append(PlanEntry(
                key=f"{doc_path}#<error>", direction=None, governs="",
                doc_hash=None, code_hash=None,
                verdict="error", on_frontier=False, error=managed.error))
            continue
        for binding in managed.bindings:
            doc_region = resolve_doc_region(root, doc_path, binding)
            for gov_file in resolve_governed_files(root, binding.governs):
                code_region = resolve_code_region(
                    root, gov_file, binding.code_anchor)
                key = f"{doc_path}#{binding.doc_anchor}"
                doc_hash = _safe_hash(root, doc_region)
                code_hash = _safe_hash(root, code_region)
                resolved.append(_Resolved(
                    key=key, direction=managed.direction,
                    governs=str(gov_file), doc_region=doc_region,
                    code_region=code_region, binding=binding,
                    doc_hash=doc_hash, code_hash=code_hash))
                doc_nodes.append(DocNode(key=key, region=code_region))
                if (root / gov_file).suffix == ".py":
                    py_files.add(gov_file)

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
        on_frontier = (not changed.available or r.key in frontier_keys
                       or code_changed or doc_changed)

        if not on_frontier:
            entries.append(_entry(r, VerdictKind.IN_SYNC, on_frontier=False))
            continue

        if judge is None:
            entries.append(_entry(r, VerdictKind.NEEDS_JUDGE, on_frontier=True))
            continue
        item = build_frontier(root, r.key, r.direction, r.binding,
                              r.doc_region, r.code_region)
        verdict = judge(item)
        entries.append(_entry(r, verdict.verdict, on_frontier=True,
                              rationale=verdict.rationale))

    entries.sort(key=lambda e: e.key)
    return Plan(base=base, diff_available=changed.available,
                judged=judge is not None, entries=entries)


def _entry(r: _Resolved, verdict: VerdictKind, on_frontier: bool,
           rationale: str = "") -> PlanEntry:
    return PlanEntry(
        key=r.key, direction=r.direction.value, governs=r.governs,
        doc_hash=r.doc_hash, code_hash=r.code_hash,
        verdict=verdict.value, on_frontier=on_frontier, rationale=rationale)


def _safe_hash(root: Path, region: Region) -> str | None:
    try:
        return hash_span(region.text(root))
    except (OSError, UnicodeDecodeError):
        return None


def _all_py(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*.py")
            if "__pycache__" not in p.parts}


def _changed_code_keys(graph, changed: ChangedSet) -> set[str]:
    keys: set[str] = set()
    for key, node in graph.code.items():
        if changed.overlaps(Path(node.path), node.lineno, node.end_lineno):
            keys.add(key)
    return keys
