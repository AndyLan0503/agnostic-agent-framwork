"""Launch a contained, unattended agent run ("good night, have fun").

Harness-pluggable (--harness claude|codex):

- claude: headless Claude Code with the gnhf settings profile - prompts
  bypassed, containment via the profile's deny rules and the
  scripts/gnhf_guard.py hook (docs/adr/0002). Resumes the same session
  after a usage-limit pause.
- codex: `codex exec` inside its OS sandbox (workspace-write: edits
  confined to the workspace, network disabled by default - keep it that
  way). Resumes with a fresh exec that continues from the durable
  artifacts (HANDOFF.md + gnhf/ branch checkpoints), which is all the
  state the run keeps anyway.

Usage: python3 scripts/gnhf.py "the feature request" [--harness codex]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SETTINGS = ".claude/gnhf-settings.json"
USAGE_LIMIT = re.compile(r"usage limit reached\|(\d+)", re.IGNORECASE)
RATE_LIMIT_TEXT = re.compile(r"rate limit|usage limit", re.IGNORECASE)

START_PROMPT = "Follow skills/unattended-run/SKILL.md for this request: {request}"
CONTINUE_PROMPT = (
    "Continue the unattended run per skills/unattended-run/SKILL.md for this "
    "request: {request}. A previous session already started it - read "
    "HANDOFF.md and the latest gnhf/ branch checkpoints first, then continue "
    "from where it left off."
)


def parse_reset_epoch(text: str) -> int | None:
    match = USAGE_LIMIT.search(text)
    return int(match.group(1)) if match else None


def looks_rate_limited(text: str) -> bool:
    return bool(RATE_LIMIT_TEXT.search(text))


def build_command(request: str, resume: bool, settings: str,
                  harness: str = "claude") -> list[str]:
    if harness == "codex":
        prompt = (CONTINUE_PROMPT if resume else START_PROMPT).format(request=request)
        return ["codex", "exec", "--sandbox", "workspace-write", prompt]
    if resume:
        prompt = "Continue the unattended run per skills/unattended-run/SKILL.md."
        return ["claude", "-c", "-p", prompt, "--settings", settings]
    return ["claude", "-p", START_PROMPT.format(request=request),
            "--settings", settings]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="the feature request to run unattended")
    parser.add_argument("--harness", choices=["claude", "codex"], default="claude")
    parser.add_argument("--settings", default=DEFAULT_SETTINGS,
                        help="containment profile (claude harness only)")
    parser.add_argument("--max-waits", type=int, default=8,
                        help="how many usage-limit windows to wait through")
    parser.add_argument("--wait-seconds", type=int, default=900,
                        help="fallback wait when the limit message has no reset time")
    args = parser.parse_args(argv)

    if not Path("AGENTS.md").exists():
        print("run from the repository root (AGENTS.md not found)", file=sys.stderr)
        return 1
    if args.harness == "claude" and not Path(args.settings).exists():
        print(f"settings profile not found: {args.settings}", file=sys.stderr)
        return 1

    resume, waits = False, 0
    while True:
        proc = subprocess.run(
            build_command(args.request, resume=resume, settings=args.settings,
                          harness=args.harness),
            capture_output=True, text=True,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)

        out = proc.stdout + proc.stderr
        epoch = parse_reset_epoch(out)
        if epoch is not None:
            delay = max(60, epoch - int(time.time()) + 60)
        elif proc.returncode != 0 and looks_rate_limited(out):
            delay = args.wait_seconds
        else:
            return proc.returncode

        if waits >= args.max_waits:
            print("gnhf: max usage-limit waits reached; stopping", file=sys.stderr)
            return 1
        print(f"gnhf: usage limit hit; sleeping {delay}s", file=sys.stderr)
        time.sleep(delay)
        resume, waits = True, waits + 1


if __name__ == "__main__":
    sys.exit(main())
