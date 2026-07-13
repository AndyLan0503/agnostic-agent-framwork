"""PreToolUse guard for unattended (gnhf) runs.

Blocks edits outside the repository, remote git actions, network commands
and web tools. Hooks run on every tool call regardless of permission mode,
so this holds even with prompts bypassed (framework/docs/adr/0002). Defense, not
proof: for a hard guarantee, run the whole session network-isolated.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
NETWORK_TOOLS = {"WebFetch", "WebSearch"}

# Local-only subcommands of otherwise-blocked tools. Criterion for adding
# one: fully local - no network, no remote mutation, no secret reads, and
# no flag can introduce a remote source (which is why `helm template` and
# `terraform plan` are absent). A safe pattern must match the ENTIRE
# command - no chaining, substitution or redirection - so it cannot
# smuggle a blocked command through.
SAFE_ARGS = r"(\s+[-\w./=:,*\"']+)*\s*"
SAFE_BASH = [
    re.compile(r"^\s*terraform\s+(fmt|validate|version)" + SAFE_ARGS + r"$"),
    re.compile(r"^\s*helm\s+(lint|version)" + SAFE_ARGS + r"$"),
    re.compile(r"^\s*git\s+remote(\s+-v)?\s*$"),
    re.compile(r"^\s*twine\s+check" + SAFE_ARGS + r"$"),
]

BLOCKED_BASH = [
    (re.compile(r"\bgit\s+(push|pull|fetch|remote)\b"), "remote git actions"),
    (re.compile(r"\bgh\b"), "GitHub CLI"),
    (re.compile(r"\b(gcloud|aws|az|kubectl|helm|terraform)\b"), "cloud and infra CLIs"),
    (re.compile(r"\b(curl|wget|ssh|scp|rsync|nc|telnet)\b"), "network commands"),
    (re.compile(r"\b(docker|podman)\s+(push|login)\b"), "registry writes"),
    (re.compile(r"\b(npm|yarn|pnpm)\s+publish\b"), "package publishing"),
    (re.compile(r"\btwine\b"), "package publishing"),
]


def classify(tool_name: str, tool_input: dict, repo_root, cwd) -> tuple[bool, str]:
    """Return (allowed, reason). Reason is set only when blocked."""
    if tool_name in NETWORK_TOOLS:
        return False, f"{tool_name} is blocked: no external connections in unattended runs"

    if tool_name in EDIT_TOOLS:
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        path = Path(raw)
        resolved = (path if path.is_absolute() else Path(cwd) / path).resolve()
        if not resolved.is_relative_to(Path(repo_root).resolve()):
            return False, f"edit outside the repository is blocked: {resolved}"

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if any(pattern.match(command) for pattern in SAFE_BASH):
            return True, ""
        for pattern, label in BLOCKED_BASH:
            if pattern.search(command):
                return False, f"blocked in unattended runs ({label})"

    return True, ""


def main() -> int:
    event = json.load(sys.stdin)
    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    allowed, reason = classify(
        event.get("tool_name", ""),
        event.get("tool_input") or {},
        repo_root=repo_root,
        cwd=event.get("cwd") or os.getcwd(),
    )
    if allowed:
        return 0
    print(f"gnhf guard: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
