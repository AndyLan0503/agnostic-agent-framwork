import subprocess
import tempfile
import unittest
from pathlib import Path

import adopt


def make_git_repo(path: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        dest = path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    for cmd in [
        ["git", "init", "-q", "-b", "main"],
        ["git", "add", "-A"],
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x"],
    ]:
        subprocess.run(cmd, cwd=path, check=True)


class ScaffoldFilesTest(unittest.TestCase):
    def test_excludes_framework_own_files(self):
        rels = adopt.scaffold_files()
        self.assertNotIn(Path("README.md"), rels)
        self.assertNotIn(Path("framework/scripts/adopt.py"), rels)
        self.assertNotIn(Path("framework/scripts/test_adopt.py"), rels)
        self.assertFalse(any(r.parts[0] == ".git" for r in rels))
        self.assertFalse(any("settings.local.json" in r.parts for r in rels))
        self.assertFalse(any("__pycache__" in r.parts for r in rels))

    def test_includes_the_scaffold(self):
        rels = adopt.scaffold_files()
        for expected in [
            Path("AGENTS.md"),
            Path("CLAUDE.md"),
            Path(".claude/settings.json"),
            Path(".claude/gnhf-settings.json"),
            Path(".claude/commands/ship.md"),
            Path("framework/scripts/gnhf.py"),
            Path("framework/scripts/gnhf_guard.py"),
            Path("framework/scripts/test_gnhf_guard.py"),
            Path("framework/roles/implementer.md"),
            Path("framework/skills/unattended-run/SKILL.md"),
            Path("framework/skills/adopt-framework/SKILL.md"),
            Path("framework/knowledge/README.md"),
            Path("framework/docs/adr/0000-template.md"),
        ]:
            self.assertIn(expected, rels)


class AdoptTest(unittest.TestCase):
    def test_copies_scaffold_into_empty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            result = adopt.adopt(target)
            self.assertEqual(result.kept, [])
            self.assertEqual(result.conflicted, [])
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "framework/scripts/gnhf_guard.py").is_file())
            self.assertIn(Path("AGENTS.md"), result.copied)

    def test_differing_existing_file_gets_framework_new_beside_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / "CLAUDE.md"
            existing.write_text("project-specific content")
            result = adopt.adopt(target)
            self.assertEqual(existing.read_text(), "project-specific content")
            self.assertIn(Path("CLAUDE.md"), result.conflicted)
            self.assertNotIn(Path("CLAUDE.md"), result.copied)
            framework_new = target / "CLAUDE.md.framework-new"
            self.assertTrue(framework_new.is_file())
            self.assertEqual(
                framework_new.read_text(),
                (adopt.FRAMEWORK_ROOT / "CLAUDE.md").read_text(),
            )

    def test_identical_existing_file_is_kept_without_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            source = adopt.FRAMEWORK_ROOT / "CLAUDE.md"
            existing = target / "CLAUDE.md"
            existing.write_text(source.read_text())
            result = adopt.adopt(target)
            self.assertIn(Path("CLAUDE.md"), result.kept)
            self.assertNotIn(Path("CLAUDE.md"), result.conflicted)
            self.assertFalse((target / "CLAUDE.md.framework-new").exists())


class UpdateTest(unittest.TestCase):
    """Re-adopting against an evolved framework, with a recorded base version."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.framework = tmp / "framework"
        self.framework.mkdir()
        make_git_repo(self.framework, {
            "AGENTS.md": "guardrails v1\n",
            "framework/roles/implementer.md": "role v1\n",
        })
        self.target = tmp / "target"
        self.target.mkdir()
        adopt.adopt(self.target, root=self.framework)

    def tearDown(self):
        self._tmp.cleanup()

    def commit_framework_change(self, rel, content):
        (self.framework / rel).write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=self.framework, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "evolve"],
            cwd=self.framework, check=True,
        )

    def test_records_framework_version_on_adopt(self):
        sha = (self.target / ".framework-version").read_text().strip()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.framework,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(sha, head)

    def test_untouched_file_fast_forwards_on_update(self):
        self.commit_framework_change("AGENTS.md", "guardrails v2\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("AGENTS.md"), result.updated)
        self.assertEqual((self.target / "AGENTS.md").read_text(), "guardrails v2\n")
        self.assertFalse((self.target / "AGENTS.md.framework-new").exists())

    def test_customized_file_with_unchanged_framework_stays_quiet(self):
        (self.target / "AGENTS.md").write_text("guardrails v1 + my invariants\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("AGENTS.md"), result.kept)
        self.assertEqual(result.conflicted, [])
        self.assertFalse((self.target / "AGENTS.md.framework-new").exists())
        self.assertEqual(
            (self.target / "AGENTS.md").read_text(),
            "guardrails v1 + my invariants\n",
        )

    def test_both_changed_is_a_conflict(self):
        (self.target / "AGENTS.md").write_text("guardrails v1 + my invariants\n")
        self.commit_framework_change("AGENTS.md", "guardrails v2\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("AGENTS.md"), result.conflicted)
        self.assertEqual(
            (self.target / "AGENTS.md.framework-new").read_text(),
            "guardrails v2\n",
        )


class RemoteAdoptTest(unittest.TestCase):
    def test_fetches_and_adopts_from_a_git_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "framework-src"
            source.mkdir()
            make_git_repo(source, {
                "AGENTS.md": "# AGENTS",
                "framework/roles/implementer.md": "role",
                "README.md": "framework readme",
            })
            target = tmp / "target"
            target.mkdir()

            root = adopt.fetch_framework(str(source), tmp / "clone")
            result = adopt.adopt(target, root=root)

            self.assertEqual((target / "AGENTS.md").read_text(), "# AGENTS")
            self.assertEqual((target / "framework/roles/implementer.md").read_text(), "role")
            self.assertFalse((target / "README.md").exists())
            self.assertIn(Path("AGENTS.md"), result.copied)


if __name__ == "__main__":
    unittest.main()
