"""Launch a contained, unattended agent run ("good night, have fun").

Starts Claude Code headless with the gnhf settings profile: permission
prompts bypassed, containment enforced by the profile's deny rules and the
scripts/gnhf_guard.py hook (docs/adr/0002). When a usage limit is hit,
sleeps until the reset window and resumes the same session. Never pushes.

Usage: python3 scripts/gnhf.py "the feature request"
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


def parse_reset_epoch(text: str) -> int | None:
    match = USAGE_LIMIT.search(text)
    return int(match.group(1)) if match else None


def build_command(request: str, resume: bool, settings: str) -> list[str]:
    if resume:
        prompt = "Continue the unattended run per skills/unattended-run/SKILL.md."
        return ["claude", "-c", "-p", prompt, "--settings", settings]
    prompt = f"Follow skills/unattended-run/SKILL.md for this request: {request}"
    return ["claude", "-p", prompt, "--settings", settings]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="the feature request to run unattended")
    parser.add_argument("--settings", default=DEFAULT_SETTINGS)
    parser.add_argument("--max-waits", type=int, default=8,
                        help="how many usage-limit windows to wait through")
    args = parser.parse_args(argv)

    if not Path("AGENTS.md").exists():
        print("run from the repository root (AGENTS.md not found)", file=sys.stderr)
        return 1
    if not Path(args.settings).exists():
        print(f"settings profile not found: {args.settings}", file=sys.stderr)
        return 1

    resume, waits = False, 0
    while True:
        proc = subprocess.run(
            build_command(args.request, resume=resume, settings=args.settings),
            capture_output=True, text=True,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)

        epoch = parse_reset_epoch(proc.stdout + proc.stderr)
        if epoch is None:
            return proc.returncode
        if waits >= args.max_waits:
            print("gnhf: max usage-limit waits reached; stopping", file=sys.stderr)
            return 1
        delay = max(60, epoch - int(time.time()) + 60)
        print(f"gnhf: usage limit hit; sleeping {delay}s until reset", file=sys.stderr)
        time.sleep(delay)
        resume, waits = True, waits + 1


if __name__ == "__main__":
    sys.exit(main())
