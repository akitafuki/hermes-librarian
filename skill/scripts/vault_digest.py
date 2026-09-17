#!/usr/bin/env python3
"""
Hermes Skill Script: Fetch links archived in the past N days for weekly synthesis briefings.

Usage:
    python vault_digest.py [--days 7]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(os.environ.get("HLIB_ROOT", Path(__file__).resolve().parent.parent.parent)).resolve()
CLI_PATH = BASE_DIR / "cli.py"
PYTHON_BIN = BASE_DIR / ".venv" / "bin" / "python"
if not PYTHON_BIN.exists():
    PYTHON_BIN = "python3"

def main():
    parser = argparse.ArgumentParser(description="Fetch links saved in the past N days for synthesis.")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--save", action="store_true", help="Save briefing directly to Obsidian vault (vault/briefings/)")
    parser.add_argument("--title", help="Custom briefing title")
    parser.add_argument("--notes", help="Executive summary / synthesis for the briefing")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    cmd = [str(PYTHON_BIN), str(CLI_PATH), "digest", "--days", str(args.days)]
    if args.save:
        cmd.append("--save")
    if args.title:
        cmd.extend(["--title", args.title])
    if args.notes:
        cmd.extend(["--notes", args.notes])
    if args.json:
        cmd.append("--json")

    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
