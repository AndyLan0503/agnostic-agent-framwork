import contextlib
import io
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import adopt


def head_content(rel: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(adopt.FRAMEWORK_ROOT), "show", f"HEAD:{rel}"],
        capture_output=True, check=True,
    ).stdout


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

    def test_excludes_framework_dev_artifacts(self):
        rels = adopt.scaffold_files()
        self.assertNotIn(Path("knowform.lock"), rels)
        adrs = {r for r in rels if r.parent.as_posix() == "framework/docs/adr"}
        self.assertEqual(adrs, {
            Path("framework/docs/adr/0000-template.md"),
            Path("framework/docs/adr/README.md"),
        })
        specs = {r for r in rels if r.parent.as_posix() == "framework/docs/specs"}
        self.assertEqual(specs, {Path("framework/docs/specs/README.md")})

    def test_future_adrs_and_specs_are_excluded_structurally(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_git_repo(root, {
                "AGENTS.md": "x",
                "framework/docs/adr/0000-template.md": "x",
                "framework/docs/adr/README.md": "x",
                "framework/docs/adr/0007-future-decision.md": "x",
                "framework/docs/specs/README.md": "x",
                "framework/docs/specs/future-feature.md": "x",
            })
            rels = adopt.scaffold_files(root)
            self.assertNotIn(Path("framework/docs/adr/0007-future-decision.md"), rels)
            self.assertNotIn(Path("framework/docs/specs/future-feature.md"), rels)
            self.assertIn(Path("framework/docs/adr/0000-template.md"), rels)
            self.assertIn(Path("framework/docs/adr/README.md"), rels)
            self.assertIn(Path("framework/docs/specs/README.md"), rels)

    def test_dirty_checkout_matches_clean_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            src.mkdir()
            make_git_repo(src, {
                "AGENTS.md": "x",
                "framework/roles/implementer.md": "x",
            })
            clone = adopt.fetch_framework(str(src), tmp / "clone")
            (src / "local-notes.pdf").write_text("untracked")
            (src / "framework" / "draft.md").write_text("untracked")
            (src / "framework" / "staged.md").write_text("staged, uncommitted")
            subprocess.run(["git", "add", "framework/staged.md"], cwd=src, check=True)
            (src / "AGENTS.md").write_text("dirty working tree")
            (src / "framework" / "roles" / "implementer.md").unlink()
            rels = adopt.scaffold_files(src)
            self.assertNotIn(Path("local-notes.pdf"), rels)
            self.assertNotIn(Path("framework/draft.md"), rels)
            self.assertNotIn(Path("framework/staged.md"), rels)
            self.assertIn(Path("framework/roles/implementer.md"), rels)
            self.assertEqual(rels, adopt.scaffold_files(clone))

    def test_symlinks_and_gitlinks_never_ship(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_git_repo(root, {"AGENTS.md": "x"})
            (root / "alias.md").symlink_to("AGENTS.md")
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root,
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "update-index", "--add",
                 "--cacheinfo", f"160000,{head},vendor"],
                cwd=root, check=True,
            )
            subprocess.run(["git", "add", "alias.md"], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "-q", "-m", "links"],
                cwd=root, check=True,
            )
            rels = adopt.scaffold_files(root)
            self.assertIn(Path("AGENTS.md"), rels)
            self.assertNotIn(Path("alias.md"), rels)
            self.assertNotIn(Path("vendor"), rels)

    def test_errors_clearly_outside_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                adopt.scaffold_files(Path(tmp))
            self.assertIn("not a git repository", str(ctx.exception))

    def test_errors_on_non_repo_dir_nested_inside_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            make_git_repo(outer, {"AGENTS.md": "x"})
            nested = outer / "nested"
            nested.mkdir()
            with self.assertRaises(SystemExit) as ctx:
                adopt.scaffold_files(nested)
            self.assertIn("not a git repository", str(ctx.exception))

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
            self.assertEqual(framework_new.read_bytes(), head_content("CLAUDE.md"))

    def test_installs_committed_content_when_working_file_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src, target = tmp / "src", tmp / "target"
            src.mkdir()
            target.mkdir()
            make_git_repo(src, {
                "AGENTS.md": "x\n",
                "framework/roles/implementer.md": "role v1\n",
            })
            (src / "framework/roles/implementer.md").unlink()
            result = adopt.adopt(target, root=src)
            self.assertIn(Path("framework/roles/implementer.md"), result.copied)
            self.assertEqual(
                (target / "framework/roles/implementer.md").read_text(), "role v1\n")
            self.assertTrue((target / ".framework-version").is_file())

    def test_installs_committed_bytes_not_dirty_working_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src, target = tmp / "src", tmp / "target"
            src.mkdir()
            target.mkdir()
            make_git_repo(src, {"AGENTS.md": "committed\n"})
            (src / "AGENTS.md").write_text("dirty\n")
            adopt.adopt(target, root=src)
            self.assertEqual((target / "AGENTS.md").read_text(), "committed\n")

    def test_dirty_local_install_equals_clone_install(self):
        def tree(root: Path) -> dict:
            return {p.relative_to(root): p.read_bytes()
                    for p in root.rglob("*") if p.is_file()}

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            src.mkdir()
            make_git_repo(src, {
                "AGENTS.md": "x\n",
                "framework/roles/implementer.md": "role v1\n",
            })
            clone = adopt.fetch_framework(str(src), tmp / "clone")
            (src / "AGENTS.md").write_text("dirty\n")
            (src / "framework" / "staged.md").write_text("staged")
            subprocess.run(["git", "add", "framework/staged.md"], cwd=src, check=True)
            (src / "framework/roles/implementer.md").unlink()
            (src / "untracked.pdf").write_text("untracked")

            local_target, clone_target = tmp / "t1", tmp / "t2"
            local_target.mkdir()
            clone_target.mkdir()
            adopt.adopt(local_target, root=src)
            adopt.adopt(clone_target, root=clone)
            self.assertEqual(tree(local_target), tree(clone_target))

    def test_executable_bit_survives_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src, target = tmp / "src", tmp / "target"
            src.mkdir()
            target.mkdir()
            script = src / "framework" / "scripts" / "hook.py"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env python3\n")
            script.chmod(0o755)
            make_git_repo(src, {"AGENTS.md": "x\n"})
            adopt.adopt(target, root=src)
            installed = target / "framework" / "scripts" / "hook.py"
            self.assertTrue(installed.is_file())
            self.assertTrue(installed.stat().st_mode & 0o111)

    def test_adopt_from_nested_non_repo_dir_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            outer = tmp / "outer"
            outer.mkdir()
            make_git_repo(outer, {"AGENTS.md": "x\n"})
            nested = outer / "nested"
            nested.mkdir()
            target = tmp / "target"
            target.mkdir()
            with self.assertRaises(SystemExit):
                adopt.adopt(target, root=nested)
            self.assertEqual(list(target.iterdir()), [])

    def test_identical_existing_file_is_kept_without_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / "CLAUDE.md"
            existing.write_bytes(head_content("CLAUDE.md"))
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
        first_line = (self.target / ".framework-version").read_text().splitlines()[0]
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.framework,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(first_line, head)

    def test_sha_only_version_file_still_resolves_base(self):
        version = self.target / ".framework-version"
        sha = version.read_text().splitlines()[0]
        version.write_text(sha + "\n")
        self.commit_framework_change("AGENTS.md", "guardrails v2\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("AGENTS.md"), result.updated)
        self.assertEqual((self.target / "AGENTS.md").read_text(), "guardrails v2\n")

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


class ReadVersionTest(unittest.TestCase):
    def read(self, raw: bytes):
        with tempfile.TemporaryDirectory() as tmp:
            version = Path(tmp) / ".framework-version"
            version.write_bytes(raw)
            return adopt._read_version(version)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                adopt._read_version(Path(tmp) / ".framework-version"), (None, []))

    def test_empty_file(self):
        self.assertEqual(self.read(b""), (None, []))

    def test_sha_only_old_format(self):
        self.assertEqual(self.read(b"abc123\n"), ("abc123", []))

    def test_crlf_line_endings(self):
        self.assertEqual(self.read(b"abc123\r\na.md\r\nb/c.md\r\n"),
                         ("abc123", [Path("a.md"), Path("b/c.md")]))

    def test_blank_and_whitespace_only_lines_are_skipped(self):
        self.assertEqual(self.read(b"abc123\n\n  \na.md\n\t\n"),
                         ("abc123", [Path("a.md")]))

    def test_whitespace_only_first_line_yields_no_sha(self):
        self.assertEqual(self.read(b"   \na.md\n"), (None, [Path("a.md")]))


class VersionFileTest(unittest.TestCase):
    def test_adopt_writes_sha_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src, target = tmp / "src", tmp / "target"
            src.mkdir()
            target.mkdir()
            make_git_repo(src, {
                "AGENTS.md": "x\n",
                "framework/roles/implementer.md": "role v1\n",
            })
            adopt.adopt(target, root=src)
            lines = (target / ".framework-version").read_text().splitlines()
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=src,
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            self.assertEqual(lines[0], head)
            self.assertEqual(lines[1:], ["AGENTS.md", "framework/roles/implementer.md"])


class ManifestDeletionTest(unittest.TestCase):
    """Deletion candidates come from the recorded manifest, not the base tree."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.framework = tmp / "framework"
        self.framework.mkdir()
        make_git_repo(self.framework, {
            "AGENTS.md": "guardrails v1\n",
            "framework/extra/tool.md": "tool v1\n",
            "knowform.lock": "lock\n",
        })
        self.target = tmp / "target"
        self.target.mkdir()
        adopt.adopt(self.target, root=self.framework)

    def tearDown(self):
        self._tmp.cleanup()

    def commit_framework(self, *cmds):
        for cmd in cmds:
            subprocess.run(cmd, cwd=self.framework, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "evolve"],
            cwd=self.framework, check=True,
        )

    def test_target_authored_file_at_colliding_path_is_untouched(self):
        spec = self.target / "framework/docs/specs/collide.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("target's own spec\n")
        (self.framework / "framework/docs/specs").mkdir(parents=True)
        (self.framework / "framework/docs/specs/collide.md").write_text(
            "framework spec\n")
        self.commit_framework(["git", "add", "-A"])
        # Second run's base tree contains the colliding dev artifact.
        for _ in range(2):
            result = adopt.adopt(self.target, root=self.framework)
            self.assertNotIn(Path("framework/docs/specs/collide.md"), result.removed)
            self.assertNotIn(Path("framework/docs/specs/collide.md"), result.orphaned)
        self.assertEqual(spec.read_text(), "target's own spec\n")

    def test_vendored_byte_equal_dev_artifact_survives(self):
        vendored = self.target / "knowform.lock"
        vendored.write_bytes((self.framework / "knowform.lock").read_bytes())
        result = adopt.adopt(self.target, root=self.framework)
        self.assertEqual(result.removed, [])
        self.assertEqual(result.orphaned, [])
        self.assertEqual(result.unverified, [])
        self.assertTrue(vendored.is_file())

    def test_manifest_roundtrips_across_successive_adopts(self):
        self.commit_framework(["git", "rm", "-q", "framework/extra/tool.md"])
        second = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("framework/extra/tool.md"), second.removed)
        lines = (self.target / ".framework-version").read_text().splitlines()
        self.assertNotIn("framework/extra/tool.md", lines[1:])
        self.assertIn("AGENTS.md", lines[1:])
        third = adopt.adopt(self.target, root=self.framework)
        self.assertEqual(third.removed, [])
        self.assertEqual(third.orphaned, [])
        self.assertEqual(third.unverified, [])


class DeletionTest(unittest.TestCase):
    """Pre-manifest fallback: a SHA-only .framework-version derives deletion
    candidates from the base tree, so stranded dev artifacts still clean up."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.framework = tmp / "framework"
        self.framework.mkdir()
        make_git_repo(self.framework, {
            "AGENTS.md": "guardrails v1\n",
            "framework/roles/implementer.md": "role v1\n",
            "framework/extra/tool.md": "tool v1\n",
            "framework/docs/adr/0001-past.md": "adr\n",
            "framework/docs/specs/old-feature.md": "spec\n",
            "knowform.lock": "lock\n",
        })
        self.target = tmp / "target"
        self.target.mkdir()
        adopt.adopt(self.target, root=self.framework)
        # Simulate an older adopt that shipped framework-dev artifacts and
        # recorded only the SHA (pre-manifest format).
        for rel in ["framework/docs/adr/0001-past.md",
                    "framework/docs/specs/old-feature.md",
                    "knowform.lock"]:
            dest = self.target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((self.framework / rel).read_bytes())
        version = self.target / ".framework-version"
        version.write_text(version.read_text().splitlines()[0] + "\n")

    def tearDown(self):
        self._tmp.cleanup()

    def commit_framework_removal(self, rel):
        subprocess.run(["git", "rm", "-q", rel], cwd=self.framework, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "remove"],
            cwd=self.framework, check=True,
        )

    def test_now_excluded_files_are_removed_when_untouched(self):
        result = adopt.adopt(self.target, root=self.framework)
        self.assertEqual(set(result.removed), {
            Path("framework/docs/adr/0001-past.md"),
            Path("framework/docs/specs/old-feature.md"),
            Path("knowform.lock"),
        })
        self.assertEqual(result.orphaned, [])
        self.assertFalse((self.target / "knowform.lock").exists())
        self.assertFalse((self.target / "framework/docs").exists())
        self.assertTrue((self.target / "framework/roles/implementer.md").is_file())

    def test_customized_no_longer_shipped_file_is_kept_and_reported(self):
        adr = self.target / "framework/docs/adr/0001-past.md"
        adr.write_text("adr + local edits\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("framework/docs/adr/0001-past.md"), result.orphaned)
        self.assertNotIn(Path("framework/docs/adr/0001-past.md"), result.removed)
        self.assertEqual(adr.read_text(), "adr + local edits\n")

    def test_file_deleted_from_framework_is_removed_on_update(self):
        self.commit_framework_removal("framework/extra/tool.md")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertIn(Path("framework/extra/tool.md"), result.removed)
        self.assertFalse((self.target / "framework/extra").exists())

    def test_fallback_orphan_message_never_instructs_deletion(self):
        adr = self.target / "framework/docs/adr/0001-past.md"
        adr.write_text("adr + local edits\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            adopt.main([str(self.target), "--from", str(self.framework)])
        orphan_lines = [line for line in out.getvalue().splitlines()
                        if line.lstrip().startswith("? ")]
        self.assertEqual(len(orphan_lines), 1)
        self.assertIn("framework/docs/adr/0001-past.md", orphan_lines[0])
        self.assertIn("possibly yours - review", orphan_lines[0])
        self.assertNotIn("delete", orphan_lines[0])

    def test_no_deletions_without_recorded_base(self):
        fresh = Path(self._tmp.name) / "fresh"
        fresh.mkdir()
        stray = fresh / "framework/docs/adr/0001-past.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("adr\n")
        result = adopt.adopt(fresh, root=self.framework)
        self.assertEqual(result.removed, [])
        self.assertEqual(result.orphaned, [])
        self.assertEqual(result.unverified, [])
        self.assertTrue(stray.is_file())


class TamperedStateTest(unittest.TestCase):
    """A corrupted .framework-version must never widen the deletion guard."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.framework = tmp / "framework"
        self.framework.mkdir()
        make_git_repo(self.framework, {
            "AGENTS.md": "guardrails v1\n",
            "framework/extra/tool.md": "tool v1\n",
        })
        self.target = tmp / "target"
        self.target.mkdir()
        adopt.adopt(self.target, root=self.framework)
        self.version = self.target / ".framework-version"

    def tearDown(self):
        self._tmp.cleanup()

    def drop_from_framework(self, rel):
        subprocess.run(["git", "rm", "-q", rel], cwd=self.framework, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "remove"],
            cwd=self.framework, check=True,
        )

    def test_escaping_manifest_paths_delete_nothing(self):
        tmp = Path(self._tmp.name)
        abs_victim = tmp / "abs-victim.txt"
        abs_victim.write_text("outside the target\n")
        rel_victim = tmp / "rel-victim.txt"
        rel_victim.write_text("outside the target\n")
        self.version.write_text(
            self.version.read_text() + str(abs_victim) + "\n../rel-victim.txt\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertEqual(result.removed, [])
        self.assertEqual(set(result.unverified),
                         {Path(str(abs_victim)), Path("../rel-victim.txt")})
        self.assertEqual(abs_victim.read_text(), "outside the target\n")
        self.assertEqual(rel_victim.read_text(), "outside the target\n")

    def test_unresolvable_base_sha_deletes_nothing(self):
        self.drop_from_framework("framework/extra/tool.md")
        lines = self.version.read_text().splitlines()
        self.version.write_text("\n".join(["0" * 40, *lines[1:]]) + "\n")
        result = adopt.adopt(self.target, root=self.framework)
        self.assertEqual(result.removed, [])
        self.assertEqual(result.unverified, [Path("framework/extra/tool.md")])
        self.assertEqual(
            (self.target / "framework/extra/tool.md").read_text(), "tool v1\n")

    def test_unverifiable_orphan_message_avoids_customized_and_delete(self):
        self.drop_from_framework("framework/extra/tool.md")
        lines = self.version.read_text().splitlines()
        self.version.write_text("\n".join(["0" * 40, *lines[1:]]) + "\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            adopt.main([str(self.target), "--from", str(self.framework)])
        orphan_lines = [line for line in out.getvalue().splitlines()
                        if line.lstrip().startswith("? ")]
        self.assertEqual(len(orphan_lines), 1)
        self.assertIn("framework/extra/tool.md", orphan_lines[0])
        self.assertIn("base unverifiable - review", orphan_lines[0])
        self.assertNotIn("customized", orphan_lines[0])
        self.assertNotIn("delete", orphan_lines[0])


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

    def test_clone_failure_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with self.assertRaises(SystemExit) as ctx:
                adopt.fetch_framework(str(tmp / "no-such-repo"), tmp / "dest")
            message = str(ctx.exception)
            self.assertIn("git clone failed", message)
            self.assertNotEqual(message.strip(), "git clone failed:")


class CitationSweepTest(unittest.TestCase):
    """Shipped files must not reference framework-side artifacts."""

    ADR_PATH = re.compile(r"framework/docs/adr/(\d{4})")

    def shipped_texts(self):
        for rel in adopt.scaffold_files():
            yield rel, (adopt.FRAMEWORK_ROOT / rel).read_text(errors="ignore")

    def test_no_shipped_file_cites_a_non_shipped_adr_path(self):
        for rel, text in self.shipped_texts():
            for num in self.ADR_PATH.findall(text):
                self.assertEqual(
                    num, "0000",
                    f"{rel} cites framework/docs/adr/{num}, which does not ship",
                )

    def test_no_shipped_file_references_the_adopt_make_target(self):
        for rel, text in self.shipped_texts():
            self.assertNotIn("make adopt", text, f"{rel} references make adopt")
        makefile = (adopt.FRAMEWORK_ROOT / "Makefile").read_text()
        self.assertNotRegex(makefile, r"(?m)^adopt:")


if __name__ == "__main__":
    unittest.main()
