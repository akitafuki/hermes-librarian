#!/usr/bin/env python3
"""
Hermes Skill Script: Update reading status, tags, or notes on an archived link.

Usage:
    python vault_triage.py "<id_or_url>" [--status inbox|reading|archived|favorite] [--tags "..."] [--notes "..."]
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
    parser = argparse.ArgumentParser(description="Update link status, tags, or notes.")
    parser.add_argument("target", help="Link ID or URL")
    parser.add_argument("--status", choices=["inbox", "reading", "archived", "favorite"])
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--notes", help="Personal notes")
    args = parser.parse_args()

    cmd = [str(PYTHON_BIN), str(CLI_PATH), "update", args.target]
    if args.status:
        cmd.extend(["--status", args.status])
    if args.tags:
        cmd.extend(["--tags", args.tags])
    if args.notes:
        cmd.extend(["--notes", args.notes])

    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
