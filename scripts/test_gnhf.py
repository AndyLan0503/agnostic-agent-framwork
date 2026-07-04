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


if __name__ == "__main__":
    unittest.main()
