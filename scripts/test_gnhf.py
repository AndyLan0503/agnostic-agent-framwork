import unittest

import gnhf


class ParseResetTest(unittest.TestCase):
    def test_parses_reset_epoch_from_limit_message(self):
        text = "Claude AI usage limit reached|1751500000"
        self.assertEqual(gnhf.parse_reset_epoch(text), 1751500000)

    def test_returns_none_when_no_limit_hit(self):
        self.assertIsNone(gnhf.parse_reset_epoch("run finished cleanly"))


class BuildCommandTest(unittest.TestCase):
    SETTINGS = ".claude/gnhf-settings.json"

    def test_first_command_uses_profile_and_skill_prompt(self):
        cmd = gnhf.build_command("add feature x", resume=False, settings=self.SETTINGS)
        self.assertEqual(cmd[0], "claude")
        self.assertIn("--settings", cmd)
        self.assertIn(self.SETTINGS, cmd)
        self.assertNotIn("-c", cmd)
        prompt = cmd[cmd.index("-p") + 1]
        self.assertIn("skills/unattended-run/SKILL.md", prompt)
        self.assertIn("add feature x", prompt)

    def test_resume_command_continues_same_session_with_profile(self):
        cmd = gnhf.build_command("add feature x", resume=True, settings=self.SETTINGS)
        self.assertIn("-c", cmd)
        self.assertIn("--settings", cmd)
        self.assertIn(self.SETTINGS, cmd)


class CodexCommandTest(unittest.TestCase):
    def test_first_command_runs_headless_in_os_sandbox(self):
        cmd = gnhf.build_command("add feature x", resume=False,
                                 settings=gnhf.DEFAULT_SETTINGS, harness="codex")
        self.assertEqual(cmd[:2], ["codex", "exec"])
        self.assertIn("--sandbox", cmd)
        self.assertIn("workspace-write", cmd)
        prompt = cmd[-1]
        self.assertIn("skills/unattended-run/SKILL.md", prompt)
        self.assertIn("add feature x", prompt)

    def test_resume_is_a_fresh_exec_continuing_from_artifacts(self):
        cmd = gnhf.build_command("add feature x", resume=True,
                                 settings=gnhf.DEFAULT_SETTINGS, harness="codex")
        self.assertEqual(cmd[:2], ["codex", "exec"])
        prompt = cmd[-1]
        self.assertIn("HANDOFF.md", prompt)
        self.assertIn("add feature x", prompt)


class RateLimitTextTest(unittest.TestCase):
    def test_detects_generic_rate_limit_text(self):
        self.assertTrue(gnhf.looks_rate_limited("Rate limit reached; try later"))
        self.assertTrue(gnhf.looks_rate_limited("usage limit hit"))
        self.assertFalse(gnhf.looks_rate_limited("run finished cleanly"))


if __name__ == "__main__":
    unittest.main()
