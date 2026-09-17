"""End-to-end: the shipped suite must pass in a repository that adopted it.

Every module under `framework/scripts/` is copied verbatim into every
adopting repository, so each test runs in two places with different truths:
here, where this checkout *is* the framework, and there, where it is not. A
test that asserts a framework-only fact without guarding on that difference
is green here and red in every adopted repo on its first `make test` - which
is what shipped in 201dc4f and what this module exists to prevent.

The check is the real thing rather than a proxy: build a tree that reads as
an adopted copy - the working tree plus a `.framework-version` - and run the
whole suite inside it. Anything that depends on being the framework
repository fails here, once, before it reaches an adopter.

This module is framework-side only: `adopt.EXCLUDED_FILES` keeps it out of
what adoption ships, so the child run cannot re-enter it and recurse. That
exclusion is itself asserted below rather than trusted.

Stdlib only, Python 3.9 floor (AGENTS.md "Conventions").
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import adopt

ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = ".framework-version"
BINDINGS = ROOT / "knowform.bindings.json"
SUITE = ["-m", "unittest", "discover", "-s", "framework/scripts", "-p", "test_*.py"]

# `Ran N tests` from unittest's own summary - the child's scan set.
_RAN = re.compile(r"^Ran (\d+) tests?", re.MULTILINE)


def shipped_working_tree_files(root: Path) -> list:
    """What adoption would install, read from the working tree.

    Tracked plus untracked-but-not-ignored, because a test module added in
    the same change as the fix it guards is exactly what has to be covered;
    `adopt.scaffold_files` reads HEAD instead, which would test the previous
    commit. The exclusion rules come from `adopt.ships`, so the copy stays
    faithful to what an adopter actually receives.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others",
         "--exclude-standard", "-z"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise unittest.SkipTest("not a git checkout; cannot build an adopted copy")
    names = [n for n in proc.stdout.decode().split("\0") if n]
    return [n for n in names if adopt.ships(Path(n))]


def head_sha(root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True
    )
    return proc.stdout.decode().strip() or "0" * 40


class AdoptedCopyTest(unittest.TestCase):
    """The suite, run once more as an adopter would run it."""

    def test_this_module_is_not_shipped_to_adopters(self):
        """Without the exclusion, the child would run this test and recurse."""
        self.assertFalse(
            adopt.ships(Path("framework/scripts/test_adoption_smoke.py")),
            "this module must stay in adopt.EXCLUDED_FILES: shipped, it would "
            "build an adopted copy inside every adopted copy, and import an "
            "adopt.py that adoption does not install",
        )

    def test_every_drift_binding_ships(self):
        """A binding may only cite paths adoption installs.

        Cards and `knowform.bindings.json` both ship verbatim, so a binding
        naming a framework-only file resolves to nothing in every adopted repo:
        red suite, and a reconciler pointed at a file that is not there. A card
        about a framework-only mechanism therefore carries no `sources`.
        """
        entries = json.loads(BINDINGS.read_text(encoding="utf-8"))["markdown"]
        self.assertTrue(entries, "no drift bindings found; nothing was checked")
        unshipped = sorted({
            path
            for entry in entries
            for path in (entry["doc"], entry["governs"])
            if not adopt.ships(Path(path))
        })
        self.assertEqual(
            unshipped, [],
            f"drift binding(s) cite path(s) adoption does not ship: {unshipped}. "
            f"Either the path should ship, or the card should drop its "
            f"`sources` and its binding.",
        )
        print(f"bindings: {len(entries)} checked")

    def test_the_suite_passes_in_an_adopted_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "adopted"
            dest.mkdir()
            copied = self._build_adopted_copy(dest)

            result = subprocess.run(
                [sys.executable, *SUITE], cwd=str(dest),
                capture_output=True, text=True,
            )

        ran = _RAN.search(result.stderr)
        self.assertIsNotNone(
            ran,
            f"the adopted copy produced no unittest summary, so nothing ran:\n"
            f"{result.stderr[-4000:]}",
        )
        count = int(ran.group(1))
        self.assertGreater(
            count, 0, "the adopted copy ran zero tests; the check examined nothing"
        )
        self.assertEqual(
            result.returncode, 0,
            f"the suite fails in a repository that adopted it. Every failure "
            f"below reaches every adopter on their first `make test`; guard the "
            f"framework-only assertion the way "
            f"`test_no_deferral_in_this_repository_has_expired` does.\n\n"
            f"{result.stderr[-6000:]}",
        )
        print(f"adopted copy: {copied} file(s) copied, {count} tests run")

    def _build_adopted_copy(self, dest: Path) -> int:
        files = shipped_working_tree_files(ROOT)
        self.assertTrue(
            files, "the working tree lists no files; the copy would be empty"
        )
        for rel in files:
            source = ROOT / rel
            if not source.is_file():
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        # What makes the copy read as adopted (CONTRIBUTING.md, "Deferral
        # dates expire here, and only here"): the version file adopt.py writes.
        (dest / VERSION_FILE).write_text(
            head_sha(ROOT) + "\n" + "\n".join(files) + "\n", encoding="utf-8"
        )

        # A real adopter's copy is a repository; several modules shell out to
        # git against their own root and would fail for the wrong reason here.
        subprocess.run(["git", "-C", str(dest), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(dest), "-c", "user.name=adoption-smoke",
             "-c", "user.email=adoption-smoke@example.invalid",
             "commit", "-q", "-m", "adopt"],
            check=True,
        )
        return len(files)


if __name__ == "__main__":
    unittest.main()
