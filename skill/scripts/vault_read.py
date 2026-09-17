#!/usr/bin/env python3
"""
Hermes Skill Script: Read full archived article Markdown and quotes (RAG retrieval).

Usage:
    python vault_read.py "<id_or_url>"
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
    parser = argparse.ArgumentParser(description="Read full archived body and highlights for a link.")
    parser.add_argument("target", help="Link ID or URL")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    cmd = [str(PYTHON_BIN), str(CLI_PATH), "view", args.target]
    if args.json:
        cmd.append("--json")

    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
