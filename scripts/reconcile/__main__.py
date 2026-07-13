"""CLI: `python3 -m reconcile {plan|sync}`.

- `plan`  - report doc↔code drift (read-only; no judge wired, zero tokens).
- `sync`  - re-bless recorded hashes into `.docstate`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .plan import plan
from .sync import sync


def _summary(result) -> str:
    lines = [f"base {result.base} | diff {'yes' if result.diff_available else 'no'}"
             f" | judged {'yes' if result.judged else 'no'}"]
    for e in result.entries:
        if e.verdict == "in-sync":
            continue
        mark = e.error or e.verdict
        lines.append(f"  {mark:<12} {e.entry_id}")
    total = sum(1 for e in result.entries if e.verdict != "in-sync")
    lines.append(f"{total} binding(s) need attention "
                 f"({len(result.entries)} total)")
    return "\n".join(lines)


def _cmd_plan(args) -> int:
    result = plan(Path(args.root), base=args.base, depth=args.depth)
    if args.format == "summary":
        print(_summary(result))
    else:
        json.dump(result.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


def _cmd_sync(args) -> int:
    result = sync(Path(args.root))
    print(f"blessed {result.blessed} binding(s), {result.errors} error(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reconcile")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="report doc↔code drift (read-only)")
    p.add_argument("--root", default=".", help="repo root to scan")
    p.add_argument("--base", default="HEAD", help="git base ref for the diff")
    p.add_argument("--depth", type=int, default=2,
                   help="IMPORTS/CALLS blast-radius depth (1-2)")
    p.add_argument("--format", choices=["json", "summary"], default="json")
    p.set_defaults(func=_cmd_plan)

    s = sub.add_parser("sync", help="re-bless recorded hashes into .docstate")
    s.add_argument("--root", default=".", help="repo root to scan")
    s.set_defaults(func=_cmd_sync)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
