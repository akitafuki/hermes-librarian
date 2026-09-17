#!/usr/bin/env python3
"""
Hermes Skill Script: Archive a URL to the Link Vault.

Usage:
    python vault_archive.py "<URL>" [--tags "tag1, tag2"] [--status inbox|reading|archived|favorite] [--notes "context"]
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
    parser = argparse.ArgumentParser(description="Archive a link into the Hermes Link Vault.")
    parser.add_argument("url", help="URL to archive")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--status", choices=["inbox", "reading", "archived", "favorite"], default="inbox")
    parser.add_argument("--notes", help="Personal framing or notes")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    cmd = [str(PYTHON_BIN), str(CLI_PATH), "add", args.url, "--status", args.status]
    if args.tags:
        cmd.extend(["--tags", args.tags])
    if args.notes:
        cmd.extend(["--notes", args.notes])
    if args.json:
        cmd.append("--json")

    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
