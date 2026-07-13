"""CLI: `python3 -m reconcile plan [--base REF] [--root DIR]`.

Read-only. Prints the drift plan as JSON. No judge is wired here, so it
costs zero tokens; a caller injects one via the library API.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .plan import plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reconcile")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="report doc↔code drift (read-only)")
    p.add_argument("--root", default=".", help="repo root to scan")
    p.add_argument("--base", default="HEAD", help="git base ref for the diff")
    p.add_argument("--depth", type=int, default=2,
                   help="IMPORTS/CALLS blast-radius depth (1-2)")
    args = parser.parse_args(argv)

    result = plan(Path(args.root), base=args.base, depth=args.depth)
    json.dump(result.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
