import tempfile
import unittest
from pathlib import Path

from reconcile.plan import plan
from reconcile.sync import sync

MANAGED = (
    "---\nreconcile:\n  direction: code-is-truth\n"
    "  bindings:\n    - doc_anchor: x\n      governs: mod.py\n---\n\n"
    "<!-- reconcile:x:start -->\nprose\n<!-- reconcile:x:end -->\n")


class IgnoreFileTest(unittest.TestCase):
    def _repo(self, tmp: Path):
        (tmp / "mod.py").write_text("def f():\n    return 1\n")
        (tmp / "real.md").write_text(MANAGED)
        fixtures = tmp / "pkg" / "tests" / "fixtures"
        fixtures.mkdir(parents=True)
        (fixtures / "mod.py").write_text("def f():\n    return 1\n")
        (fixtures / "bad.md").write_text(MANAGED)
        return tmp

    def test_reconcileignore_excludes_matching_docs(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._repo(Path(t))
            (root / ".reconcileignore").write_text("pkg/tests\n")
            keys = {e.key for e in plan(root).entries}
            self.assertIn("real.md#x", keys)
            self.assertFalse(any("bad.md" in k for k in keys), keys)

    def test_without_ignore_fixtures_are_scanned(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._repo(Path(t))
            keys = {e.key for e in plan(root).entries}
            self.assertTrue(any("bad.md" in k for k in keys), keys)

    def test_sync_honors_ignore(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._repo(Path(t))
            (root / ".reconcileignore").write_text(
                "# comment\npkg/tests\n")
            sync(root)
            from reconcile.docstate import load
            state = load(root)
            self.assertFalse(any("bad.md" in k for k in state.records), state.records)


if __name__ == "__main__":
    unittest.main()
