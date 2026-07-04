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
        self.assertNotIn(Path("scripts/adopt.py"), rels)
        self.assertNotIn(Path("scripts/test_adopt.py"), rels)
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
            Path("scripts/gnhf.py"),
            Path("scripts/gnhf_guard.py"),
            Path("scripts/test_gnhf_guard.py"),
            Path("roles/implementer.md"),
            Path("skills/unattended-run/SKILL.md"),
            Path("skills/adopt-framework/SKILL.md"),
            Path("knowledge/README.md"),
            Path("docs/adr/0000-template.md"),
        ]:
            self.assertIn(expected, rels)


class AdoptTest(unittest.TestCase):
    def test_copies_scaffold_into_empty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            copied, kept, conflicted = adopt.adopt(target)
            self.assertEqual(kept, [])
            self.assertEqual(conflicted, [])
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "scripts/gnhf_guard.py").is_file())
            self.assertIn(Path("AGENTS.md"), copied)

    def test_differing_existing_file_gets_framework_new_beside_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / "CLAUDE.md"
            existing.write_text("project-specific content")
            copied, kept, conflicted = adopt.adopt(target)
            self.assertEqual(existing.read_text(), "project-specific content")
            self.assertIn(Path("CLAUDE.md"), conflicted)
            self.assertNotIn(Path("CLAUDE.md"), copied)
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
            copied, kept, conflicted = adopt.adopt(target)
            self.assertIn(Path("CLAUDE.md"), kept)
            self.assertNotIn(Path("CLAUDE.md"), conflicted)
            self.assertFalse((target / "CLAUDE.md.framework-new").exists())


class RemoteAdoptTest(unittest.TestCase):
    def test_fetches_and_adopts_from_a_git_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "framework-src"
            source.mkdir()
            make_git_repo(source, {
                "AGENTS.md": "# AGENTS",
                "roles/implementer.md": "role",
                "README.md": "framework readme",
            })
            target = tmp / "target"
            target.mkdir()

            root = adopt.fetch_framework(str(source), tmp / "clone")
            copied, kept, conflicted = adopt.adopt(target, root=root)

            self.assertEqual((target / "AGENTS.md").read_text(), "# AGENTS")
            self.assertEqual((target / "roles/implementer.md").read_text(), "role")
            self.assertFalse((target / "README.md").exists())
            self.assertIn(Path("AGENTS.md"), copied)


if __name__ == "__main__":
    unittest.main()
