"""Changed line ranges per file, from `git diff` against a base ref.

Read-only shell-out (`git diff`, `git rev-parse`). Default base is the
working tree vs `HEAD`. Missing repo / unknown ref degrade to "no changes
known" so the caller can still emit hashes (docs/adr/0003, Tier 0).
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
DIFF_FILE = re.compile(r"^\+\+\+ b/(.*)$")


@dataclass
class ChangedSet:
    """Changed line ranges (1-based inclusive) per repo-relative file path.

    `available` is False when git could not produce a diff (not a repo,
    unknown ref); the caller treats an unavailable set as "cannot prove
    unchanged" and still emits hashes.
    """
    available: bool = True
    ranges: dict[str, list[tuple[int, int]]] = field(default_factory=dict)

    def overlaps(self, path: Path, start: int, end: int) -> bool:
        if not self.available:
            return False
        for lo, hi in self.ranges.get(str(path), []):
            if start <= hi and lo <= end:
                return True
        return False

    def touched(self, path: Path) -> bool:
        return self.available and bool(self.ranges.get(str(path)))


def _run(root: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=root,
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def _is_repo(root: Path) -> bool:
    code, _ = _run(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0


def _ref_exists(root: Path, ref: str) -> bool:
    code, _ = _run(root, ["rev-parse", "--verify", "--quiet", ref])
    return code == 0


def changed_set(root: Path, base: str = "HEAD") -> ChangedSet:
    """Line ranges changed on the NEW side of `git diff <base>`.

    base=="HEAD" (or any ref) diffs the working tree against that ref, which
    is what an editing agent sees on its own diff.
    """
    if not _is_repo(root) or not _ref_exists(root, base):
        return ChangedSet(available=False)
    code, out = _run(root, ["diff", "--unified=0", "--no-color", base])
    if code != 0:
        return ChangedSet(available=False)
    return _parse_diff(out)


def _parse_diff(out: str) -> ChangedSet:
    ranges: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in out.splitlines():
        fm = DIFF_FILE.match(line)
        if fm:
            current = fm.group(1)
            ranges.setdefault(current, [])
            continue
        hm = HUNK.match(line)
        if hm and current is not None:
            start = int(hm.group(1))
            count = int(hm.group(2)) if hm.group(2) is not None else 1
            if count == 0:
                # Pure deletion: mark the anchor line as touched.
                ranges[current].append((start, start))
            else:
                ranges[current].append((start, start + count - 1))
    return ChangedSet(ranges={k: v for k, v in ranges.items() if v})
