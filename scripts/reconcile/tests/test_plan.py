import subprocess
import tempfile
import unittest
from pathlib import Path

from reconcile.judge import JudgeInput, Verdict, VerdictKind
from reconcile.plan import plan

FIX = Path(__file__).parent / "fixtures"


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)


class RecordingJudge:
    """Injected stub judge that records every frontier item it sees."""

    def __init__(self, verdict=VerdictKind.CODE_DRIFT):
        self.calls: list[JudgeInput] = []
        self.verdict = verdict

    def __call__(self, item: JudgeInput) -> Verdict:
        self.calls.append(item)
        return Verdict(self.verdict, rationale="stub")


class PlanFixture:
    """A throwaway git repo seeded from the fixtures, committed once."""

    def __init__(self, tmp: Path):
        self.root = tmp
        for name in ["calc.py", "managed_add.md", "managed_whole.md",
                     "unmanaged.md", "no_direction.md"]:
            (self.root / name).write_text(
                (FIX / name).read_text(encoding="utf-8"), encoding="utf-8")
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@t.t")
        git(self.root, "config", "user.name", "t")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "seed")

    def edit(self, name: str, text: str) -> None:
        (self.root / name).write_text(text, encoding="utf-8")


class UnchangedCorpusTest(unittest.TestCase):
    def test_zero_tokens_and_all_in_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            judge = RecordingJudge()
            result = plan(fx.root, base="HEAD", judge=judge)
            self.assertTrue(result.diff_available)
            self.assertEqual(judge.calls, [],
                             "unchanged corpus must not invoke the judge")
            managed = [e for e in result.entries if e.verdict != "error"]
            self.assertTrue(managed)
            for e in managed:
                self.assertEqual(e.verdict, VerdictKind.IN_SYNC.value, e.key)
                self.assertFalse(e.on_frontier, e.key)

    def test_hashes_emitted_even_when_in_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            result = plan(fx.root, base="HEAD")
            e = _entry(result, "managed_add.md#add-behavior")
            self.assertTrue(e.doc_hash.startswith("sha256:"))
            self.assertTrue(e.code_hash.startswith("sha256:"))


class CodeChangeTest(unittest.TestCase):
    def test_change_reaches_frontier_and_judge(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            fx.edit("calc.py", (FIX / "calc.py").read_text()
                    .replace("return a + b", "return a + b + 1"))
            judge = RecordingJudge(VerdictKind.CODE_DRIFT)
            result = plan(fx.root, base="HEAD", judge=judge)
            e = _entry(result, "managed_add.md#add-behavior")
            self.assertTrue(e.on_frontier)
            self.assertEqual(e.verdict, VerdictKind.CODE_DRIFT.value)
            self.assertGreaterEqual(len(judge.calls), 1)
            item = judge.calls[0]
            self.assertIn("return a + b", item.code_text)
            self.assertTrue(any("def add" in s for s in item.signatures))

    def test_no_judge_yields_needs_judge_zero_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            fx.edit("calc.py", (FIX / "calc.py").read_text()
                    .replace("return a + b", "return a + b + 1"))
            result = plan(fx.root, base="HEAD", judge=None)
            e = _entry(result, "managed_add.md#add-behavior")
            self.assertTrue(e.on_frontier)
            self.assertEqual(e.verdict, VerdictKind.NEEDS_JUDGE.value)
            self.assertFalse(result.judged)


class BlastRadiusTest(unittest.TestCase):
    def test_reaches_doc_via_calls_at_depth_two(self):
        # Bind a doc to `add`; change `scaled_add`, which CALLS `add`. At
        # depth>=1 the change reaches `add`'s governed doc (widen, not narrow).
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            fx.edit("calc.py", (FIX / "calc.py").read_text()
                    .replace("return add(a, b) * factor",
                             "return add(a, b) * factor * 2"))
            judge = RecordingJudge()
            result = plan(fx.root, base="HEAD", judge=judge, depth=2)
            e = _entry(result, "managed_add.md#add-behavior")
            self.assertTrue(e.on_frontier,
                            "changed caller must reach the callee's doc")
            self.assertGreaterEqual(len(judge.calls), 1)

    def test_depth_zero_does_not_reach_indirect_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            fx.edit("calc.py", (FIX / "calc.py").read_text()
                    .replace("return add(a, b) * factor",
                             "return add(a, b) * factor * 2"))
            judge = RecordingJudge()
            result = plan(fx.root, base="HEAD", judge=judge, depth=0)
            e = _entry(result, "managed_add.md#add-behavior")
            # The symbol-scoped `add` binding is NOT reached at depth 0; only
            # the whole-file `overview` binding overlaps the change directly.
            self.assertFalse(e.on_frontier)
            judged_keys = {c.key for c in judge.calls}
            self.assertNotIn("managed_add.md#add-behavior", judged_keys)


class DirectionExplicitTest(unittest.TestCase):
    def test_missing_direction_surfaced_as_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            errors = [e for e in plan(fx.root).entries
                      if e.verdict == "error"]
            self.assertTrue(
                any("no_direction.md" in e.key for e in errors))
            for e in errors:
                self.assertIsNone(e.direction)


class ReadOnlyTest(unittest.TestCase):
    def test_plan_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = PlanFixture(Path(tmp))
            before = _snapshot(fx.root)
            plan(fx.root, base="HEAD", judge=RecordingJudge())
            self.assertEqual(before, _snapshot(fx.root))
            self.assertFalse((fx.root / ".docstate").exists())


class NoGitTest(unittest.TestCase):
    def test_non_repo_degrades_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "calc.py").write_text(
                (FIX / "calc.py").read_text(), encoding="utf-8")
            (root / "managed_add.md").write_text(
                (FIX / "managed_add.md").read_text(), encoding="utf-8")
            judge = RecordingJudge()
            result = plan(root, base="HEAD", judge=judge)
            self.assertFalse(result.diff_available)
            # No diff signal -> cannot prove unchanged; frontier is judged.
            e = _entry(result, "managed_add.md#add-behavior")
            self.assertTrue(e.on_frontier)


def _entry(result, key):
    for e in result.entries:
        if e.key == key:
            return e
    raise AssertionError(f"no entry {key}; got {[e.key for e in result.entries]}")


def _snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): p.stat().st_mtime_ns
            for p in root.rglob("*") if p.is_file()}


if __name__ == "__main__":
    unittest.main()
