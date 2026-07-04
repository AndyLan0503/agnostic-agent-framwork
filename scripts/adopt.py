"""Copy the agentic-framework scaffold into a target repository.

Existing files in the target are never overwritten: identical files are
kept silently, differing ones get the framework version written beside
them as <name>.framework-new to merge from. Then follow
skills/adopt-framework/SKILL.md inside the target.

From the framework repo:   python3 scripts/adopt.py /path/to/target-repo
From inside any repo:      python3 adopt.py . --from <framework-git-url>
(fetch this file first, e.g.
 curl -fsSL <raw-url>/scripts/adopt.py | python3 - . --from <git-url>)

Re-running against a newer framework is the update path: unchanged files
are kept, changed ones surface as .framework-new for review.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_TOP = {".git", "README.md", "HANDOFF.md"}
EXCLUDED_PARTS = {"__pycache__", ".DS_Store", "settings.local.json"}
EXCLUDED_FILES = {Path("scripts/adopt.py"), Path("scripts/test_adopt.py")}


def scaffold_files(root: Path = FRAMEWORK_ROOT) -> list[Path]:
    """Scaffold files as paths relative to the framework root."""
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts[0] in EXCLUDED_TOP or rel in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.is_file():
            files.append(rel)
    return files


def adopt(target: Path, root: Path = FRAMEWORK_ROOT) -> tuple[list[Path], list[Path], list[Path]]:
    """Copy the scaffold into target; never overwrite.

    Returns (copied, kept, conflicted). An existing file identical to the
    framework's is kept silently; a differing one is kept too, with the
    framework version written beside it as <name>.framework-new to merge
    from and then delete.
    """
    copied, kept, conflicted = [], [], []
    for rel in scaffold_files(root):
        source, dest = root / rel, target / rel
        if dest.exists():
            if dest.read_bytes() == source.read_bytes():
                kept.append(rel)
            else:
                shutil.copy2(source, dest.with_name(dest.name + ".framework-new"))
                conflicted.append(rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        copied.append(rel)
    return copied, kept, conflicted


def fetch_framework(source: str, dest: Path) -> Path:
    """Shallow-clone the framework repo (git URL or local path) into dest."""
    subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", source, str(dest)],
        check=True,
    )
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="path to the adopting repository")
    parser.add_argument("--from", dest="source", metavar="REPO",
                        help="git URL or path of the framework repo to fetch and adopt from")
    args = parser.parse_args(argv)

    if not args.target.is_dir():
        print(f"target is not a directory: {args.target}", file=sys.stderr)
        return 1

    if args.source:
        with tempfile.TemporaryDirectory() as tmp:
            root = fetch_framework(args.source, Path(tmp) / "framework")
            copied, kept, conflicted = adopt(args.target, root=root)
    else:
        copied, kept, conflicted = adopt(args.target)

    for rel in copied:
        print(f"  + {rel}")
    for rel in kept:
        print(f"  = {rel} (identical, kept)")
    for rel in conflicted:
        print(f"  ! {rel} (kept - merge from {rel}.framework-new, then delete it)")
    print(f"{len(copied)} copied, {len(kept)} identical, {len(conflicted)} to merge.")
    print("Next: follow skills/adopt-framework/SKILL.md inside the target repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
