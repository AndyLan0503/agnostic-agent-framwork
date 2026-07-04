"""Copy the agentic-framework scaffold into a target repository.

Existing files in the target are never overwritten: identical files are
kept silently, differing ones get the framework version written beside
them as <name>.framework-new to merge from. Then follow
skills/adopt-framework/SKILL.md inside the target.

From the framework repo:   python3 scripts/adopt.py /path/to/target-repo
From inside any repo:      python3 adopt.py . --from <framework-git-url>
(fetch this file first, e.g.
 curl -fsSL <raw-url>/scripts/adopt.py | python3 - . --from <git-url>)

Re-running is the update path. The framework commit last adopted is
recorded in the target's .framework-version, enabling a three-way
comparison per file: framework changed + file untouched -> fast-forward;
file customized + framework unchanged -> kept quiet; both changed ->
.framework-new to merge.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_TOP = {".git", "README.md", "HANDOFF.md"}
EXCLUDED_PARTS = {"__pycache__", ".DS_Store", "settings.local.json"}
EXCLUDED_FILES = {Path("scripts/adopt.py"), Path("scripts/test_adopt.py")}

VERSION_FILE = ".framework-version"

Result = namedtuple("Result", "copied kept updated conflicted")


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


def _framework_sha(root: Path) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def _base_content(root: Path, sha: str, rel: Path) -> bytes | None:
    """The file's content at the recorded framework commit, if resolvable."""
    proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{sha}:{rel.as_posix()}"],
        capture_output=True,
    )
    return proc.stdout if proc.returncode == 0 else None


def adopt(target: Path, root: Path = FRAMEWORK_ROOT) -> Result:
    """Copy the scaffold into target; never overwrite a customized file.

    With a .framework-version in the target, each differing file is
    compared three ways against its content at that base commit:
    framework unchanged -> local customization, kept quiet; local file
    untouched -> fast-forwarded to the new version; both changed ->
    kept, with the new version beside it as <name>.framework-new.
    Without a base, differing files all land as .framework-new.
    """
    version_file = target / VERSION_FILE
    base_sha = version_file.read_text().strip() if version_file.exists() else None

    copied, kept, updated, conflicted = [], [], [], []
    for rel in scaffold_files(root):
        source, dest = root / rel, target / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            copied.append(rel)
            continue
        current, new = dest.read_bytes(), source.read_bytes()
        if current == new:
            kept.append(rel)
            continue
        base = _base_content(root, base_sha, rel) if base_sha else None
        if base is not None and new == base:
            kept.append(rel)
        elif base is not None and current == base:
            shutil.copy2(source, dest)
            updated.append(rel)
        else:
            shutil.copy2(source, dest.with_name(dest.name + ".framework-new"))
            conflicted.append(rel)

    sha = _framework_sha(root)
    if sha:
        version_file.write_text(sha + "\n")
    return Result(copied, kept, updated, conflicted)


def fetch_framework(source: str, dest: Path) -> Path:
    """Clone the framework repo (git URL or local path) into dest.

    Full history, so updates can resolve the target's recorded base commit.
    """
    subprocess.run(["git", "clone", "--quiet", source, str(dest)], check=True)
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
            result = adopt(args.target, root=root)
    else:
        result = adopt(args.target)

    for rel in result.copied:
        print(f"  + {rel}")
    for rel in result.kept:
        print(f"  = {rel} (kept)")
    for rel in result.updated:
        print(f"  ^ {rel} (fast-forwarded to the new framework version)")
    for rel in result.conflicted:
        print(f"  ! {rel} (kept - merge from {rel}.framework-new, then delete it)")
    print(f"{len(result.copied)} copied, {len(result.kept)} kept, "
          f"{len(result.updated)} updated, {len(result.conflicted)} to merge.")
    print("Next: follow skills/adopt-framework/SKILL.md inside the target repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
