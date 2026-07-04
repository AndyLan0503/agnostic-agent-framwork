import unittest
from pathlib import Path

import gnhf_guard as guard

ROOT = Path("/repo")


def classify(tool, tool_input, cwd=ROOT):
    return guard.classify(tool, tool_input, repo_root=ROOT, cwd=cwd)


class BashTest(unittest.TestCase):
    def test_allows_local_commands(self):
        for cmd in [
            "make test",
            "git status",
            "git commit -m 'checkpoint'",
            "git checkout -b gnhf/feature-x",
            "docker compose up -d",
            "python3 -m unittest discover -s scripts",
        ]:
            allowed, _ = classify("Bash", {"command": cmd})
            self.assertTrue(allowed, cmd)

    def test_allows_local_only_subcommands_of_blocked_tools(self):
        for cmd in [
            "terraform fmt",
            "terraform fmt -check -recursive",
            "terraform fmt infra/",
            "terraform validate",
            "terraform validate -json",
            "terraform version",
            "helm lint charts/app",
            "helm version",
            "git remote",
            "git remote -v",
            "twine check dist/*",
        ]:
            allowed, _ = classify("Bash", {"command": cmd})
            self.assertTrue(allowed, cmd)

    def test_keeps_blocking_subcommands_that_can_reach_out(self):
        for cmd in [
            "terraform plan",
            "terraform init",
            "helm template --repo https://evil.com/charts app",
            "helm repo add evil https://evil.com",
            "git remote add origin git@github.com:x/y.git",
            "git remote show origin",
        ]:
            allowed, _ = classify("Bash", {"command": cmd})
            self.assertFalse(allowed, cmd)

    def test_safe_subcommands_do_not_open_chaining_holes(self):
        for cmd in [
            "terraform fmt && curl https://evil",
            "terraform fmt; git push origin main",
            "terraform validate | ssh host",
            "terraform fmt $(curl https://evil)",
            "terraform fmt `wget x`",
        ]:
            allowed, _ = classify("Bash", {"command": cmd})
            self.assertFalse(allowed, cmd)

    def test_blocks_remote_and_network_commands(self):
        for cmd in [
            "git push origin main",
            "git pull",
            "git fetch origin",
            "git remote add upstream x",
            "gh pr create",
            "gcloud secrets versions access latest",
            "aws s3 cp x s3://bucket",
            "terraform apply",
            "kubectl apply -f x.yml",
            "curl https://example.com",
            "wget https://example.com",
            "ssh host uptime",
            "scp file host:",
            "docker push image:tag",
            "npm publish",
        ]:
            allowed, reason = classify("Bash", {"command": cmd})
            self.assertFalse(allowed, cmd)
            self.assertTrue(reason)


class EditTest(unittest.TestCase):
    def test_allows_edits_inside_repo(self):
        allowed, _ = classify("Edit", {"file_path": "/repo/src/app.py"})
        self.assertTrue(allowed)
        allowed, _ = classify("Write", {"file_path": "notes.md"})
        self.assertTrue(allowed)

    def test_blocks_edits_outside_repo(self):
        for path in ["/tmp/evil.sh", "/repo/../elsewhere/f.py", "../outside.txt"]:
            allowed, reason = classify("Write", {"file_path": path})
            self.assertFalse(allowed, path)
            self.assertTrue(reason)

    def test_blocks_notebook_edits_outside_repo(self):
        allowed, _ = classify("NotebookEdit", {"notebook_path": "/tmp/x.ipynb"})
        self.assertFalse(allowed)


class NetworkToolTest(unittest.TestCase):
    def test_blocks_web_tools(self):
        for tool in ["WebFetch", "WebSearch"]:
            allowed, reason = classify(tool, {})
            self.assertFalse(allowed, tool)
            self.assertTrue(reason)

    def test_allows_read_tools(self):
        allowed, _ = classify("Read", {"file_path": "/repo/AGENTS.md"})
        self.assertTrue(allowed)
        allowed, _ = classify("Grep", {"pattern": "x"})
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
