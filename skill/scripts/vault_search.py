#!/usr/bin/env python3
"""
Hermes Skill Script: Search archived links using SQLite FTS5.

Usage:
    python vault_search.py "<query>" [--tag tag] [--status status] [--limit 10]
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
    parser = argparse.ArgumentParser(description="Search the link vault using FTS5.")
    parser.add_argument("query", nargs="?", default="", help="Search query")
    parser.add_argument("-t", "--tag", help="Filter by tag")
    parser.add_argument("-s", "--status", help="Filter by status")
    parser.add_argument("-n", "--limit", type=int, default=15, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    cmd = [str(PYTHON_BIN), str(CLI_PATH), "list", "-n", str(args.limit)]
    if args.query:
        cmd.extend(["-q", args.query])
    if args.tag:
        cmd.extend(["-t", args.tag])
    if args.status:
        cmd.extend(["-s", args.status])
    if args.json:
        cmd.append("--json")

    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
