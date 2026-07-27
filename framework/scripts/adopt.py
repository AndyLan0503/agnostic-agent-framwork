"""Copy the agentic-framework scaffold into a target repository.

The scaffold is the framework's committed state (HEAD): uncommitted
changes never ship, so a dirty checkout installs exactly what a fresh
clone of the same commit would.

Existing files in the target are never overwritten: identical files are
kept silently, differing ones get the framework version written beside
them as <name>.framework-new to merge from. Then follow
framework/skills/adopt-framework/SKILL.md inside the target.

From the framework repo:   python3 framework/scripts/adopt.py /path/to/target-repo
From inside any repo:      python3 adopt.py . --from <framework-git-url>
(fetch this file first, e.g.
 curl -fsSL <raw-url>/framework/scripts/adopt.py | python3 - . --from <git-url>)

Re-running is the update path. The target's .framework-version records
the framework commit last adopted (first line) and the manifest of files
that run installed or confirmed (following lines), enabling a three-way
comparison per file: framework changed + file untouched -> fast-forward;
file customized + framework unchanged -> kept quiet; both changed ->
.framework-new to merge. Manifest files no longer shipped are removed
when untouched, reported as orphaned when customized; paths never
recorded are never touched. A SHA-only version file (pre-manifest) falls
back to the base tree for deletion candidates once; the run then writes
a full manifest.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent

# Never shipped - the target owns its own instance.
EXCLUDED_TOP = {"README.md", "HANDOFF.md"}
EXCLUDED_FILES = {Path("framework/scripts/adopt.py"), Path("framework/scripts/test_adopt.py")}
# Framework-side development artifacts, excluded structurally so future
# ADRs and specs need no list maintenance. The pre-manifest fallback
# enumerates the base commit with them kept, so copies an earlier
# framework version shipped are detected and removed from targets.
DEV_EXCLUDED_TOP = {"knowform.lock"}
DEV_EXCLUDED_PATTERNS = [
    re.compile(r"framework/docs/adr/(?!0000-template\.md$)\d{4}-.*\.md$"),
    re.compile(r"framework/docs/specs/(?!README\.md$).*$"),
]

# ls-tree modes for regular files; symlinks (120000) and gitlinks
# (160000) never ship.
FILE_MODES = {"100644", "100755"}
EXECUTABLE_MODE = "100755"

VERSION_FILE = ".framework-version"

Result = namedtuple(
    "Result", "copied kept updated conflicted removed orphaned unverified fallback")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    except FileNotFoundError:
        raise SystemExit("git not found on PATH; adopt requires git") from None


def _require_repo_root(root: Path) -> None:
    """Fail unless root is itself a repository root.

    A plain directory nested inside some other repo would otherwise
    resolve git commands against the enclosing repo.
    """
    proc = _git(root, "rev-parse", "--show-toplevel")
    toplevel = proc.stdout.decode().strip()
    if proc.returncode != 0 or Path(toplevel).resolve() != root.resolve():
        raise SystemExit(f"not a git repository: {root}")


def _tree_entries(root: Path, ref: str, *, dev_artifacts: bool = False,
                  missing_ok: bool = False) -> dict[Path, str]:
    """Regular files at ref as {path: mode}, exclusions applied."""
    proc = _git(root, "ls-tree", "-r", "-z", ref)
    if proc.returncode != 0:
        if missing_ok:
            return {}
        raise SystemExit(
            f"git ls-tree {ref} failed in {root}: {proc.stderr.decode().strip()}")
    entries = {}
    for record in proc.stdout.decode().split("\0"):
        if not record:
            continue
        meta, name = record.split("\t", 1)
        mode = meta.split(" ", 1)[0]
        if mode not in FILE_MODES:
            continue
        rel = Path(name)
        if rel.parts[0] in EXCLUDED_TOP or rel in EXCLUDED_FILES:
            continue
        if not dev_artifacts:
            if rel.parts[0] in DEV_EXCLUDED_TOP:
                continue
            if any(pattern.fullmatch(name) for pattern in DEV_EXCLUDED_PATTERNS):
                continue
        entries[rel] = mode
    return entries


def scaffold_files(root: Path = FRAMEWORK_ROOT) -> list[Path]:
    """Shipped files as paths relative to the framework root.

    Enumerated from HEAD so a dirty local checkout installs the same set
    as a fresh clone.
    """
    _require_repo_root(root)
    return sorted(_tree_entries(root, "HEAD"))


def _read_version(version_file: Path) -> tuple[str | None, list[Path]]:
    """SHA and shipped-file manifest; a SHA-only file yields an empty manifest."""
    if not version_file.exists():
        return None, []
    lines = [line.strip() for line in version_file.read_text().splitlines()]
    sha = lines[0] if lines and lines[0] else None
    return sha, [Path(line) for line in lines[1:] if line]


def _framework_sha(root: Path) -> str | None:
    proc = _git(root, "rev-parse", "HEAD")
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def _content_at(root: Path, ref: str, rel: Path) -> bytes | None:
    """The file's content at ref, if resolvable."""
    proc = _git(root, "show", f"{ref}:{rel.as_posix()}")
    return proc.stdout if proc.returncode == 0 else None


def _write(dest: Path, content: bytes, mode: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    if mode == EXECUTABLE_MODE:
        dest.chmod(dest.stat().st_mode | 0o111)


def _prune_empty_dirs(directory: Path, stop: Path) -> None:
    while directory != stop and not any(directory.iterdir()):
        directory.rmdir()
        directory = directory.parent


def adopt(target: Path, root: Path = FRAMEWORK_ROOT) -> Result:
    """Install the scaffold at HEAD into target; never overwrite a customized file.

    With a .framework-version in the target, each differing file is
    compared three ways against its content at that base commit:
    framework unchanged -> local customization, kept quiet; local file
    untouched -> fast-forwarded to the new version; both changed ->
    kept, with the new version beside it as <name>.framework-new.
    Without a base, differing files all land as .framework-new.

    The same three-way logic extends to deletions: a manifest-recorded
    file not shipped anymore is removed if it still matches its base
    content, else kept and reported - orphaned when it differs from a
    resolvable base, unverified when the base content cannot be resolved.
    Pre-manifest targets (SHA-only version file) derive candidates from
    the base tree instead; the run then writes a full manifest.
    """
    _require_repo_root(root)
    entries = _tree_entries(root, "HEAD")
    version_file = target / VERSION_FILE
    base_sha, manifest = _read_version(version_file)

    copied, kept, updated, conflicted = [], [], [], []
    for rel in sorted(entries):
        mode, dest = entries[rel], target / rel
        new = _content_at(root, "HEAD", rel)
        if not dest.exists():
            _write(dest, new, mode)
            copied.append(rel)
            continue
        current = dest.read_bytes()
        if current == new:
            kept.append(rel)
            continue
        base = _content_at(root, base_sha, rel) if base_sha else None
        if base is not None and new == base:
            kept.append(rel)
        elif base is not None and current == base:
            _write(dest, new, mode)
            updated.append(rel)
        else:
            _write(dest.with_name(dest.name + ".framework-new"), new, mode)
            conflicted.append(rel)

    removed, orphaned, unverified = [], [], []
    fallback = base_sha is not None and not manifest
    if base_sha:
        candidates = set(manifest) if manifest else set(
            _tree_entries(root, base_sha, dev_artifacts=True, missing_ok=True))
        for rel in sorted(candidates - set(entries)):
            dest = target / rel
            if not dest.is_file():
                continue
            base = _content_at(root, base_sha, rel)
            if base is None:
                unverified.append(rel)
            elif dest.read_bytes() == base:
                dest.unlink()
                _prune_empty_dirs(dest.parent, target)
                removed.append(rel)
            else:
                orphaned.append(rel)

    sha = _framework_sha(root)
    if sha:
        version_file.write_text(
            "\n".join([sha, *(rel.as_posix() for rel in sorted(entries))]) + "\n")
    return Result(copied, kept, updated, conflicted, removed, orphaned,
                  unverified, fallback)


def fetch_framework(source: str, dest: Path) -> Path:
    """Clone the framework repo (git URL or local path) into dest.

    Full history, so updates can resolve the target's recorded base commit.
    """
    try:
        proc = subprocess.run(
            ["git", "clone", "--quiet", "--", source, str(dest)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        raise SystemExit("git not found on PATH; adopt requires git") from None
    if proc.returncode != 0:
        raise SystemExit(f"git clone failed: {proc.stderr.strip()}")
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
    for rel in result.removed:
        print(f"  - {rel} (removed - no longer shipped)")
    orphan_hint = ("no longer shipped by the framework, possibly yours - review"
                   if result.fallback else
                   "no longer shipped but customized - review, then delete")
    for rel in result.orphaned:
        print(f"  ? {rel} ({orphan_hint})")
    for rel in result.unverified:
        print(f"  ? {rel} (no longer shipped; base unverifiable - review)")
    print(f"{len(result.copied)} copied, {len(result.kept)} kept, "
          f"{len(result.updated)} updated, {len(result.conflicted)} to merge, "
          f"{len(result.removed)} removed, "
          f"{len(result.orphaned) + len(result.unverified)} orphaned.")
    print("Next: follow framework/skills/adopt-framework/SKILL.md inside the target repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
