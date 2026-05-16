#!/usr/bin/env python3
"""
Friday — Beginner Tier Main Script
Voice command → search → open images with feh
"""

import sys
import subprocess
import shutil
from pathlib import Path

# Config
LISTEN_SCRIPT = Path.home() / "friday" / "core" / "listen.py"
SEARCH_SCRIPT = Path.home() / "friday" / "core" / "search_vl_expert.py"

def run_listen():
    """Capture voice and return text."""
    result = subprocess.run(
        [sys.executable, str(LISTEN_SCRIPT)],
        capture_output=True, text=True, timeout=10
    )
    # Parse output to find the heard text
    for line in result.stdout.split("\n"):
        if line.startswith("📝 Heard: '"):
            return line.replace("📝 Heard: '", "").rstrip("'")
    return None

def run_search(query):
    """Run search and get results."""
    print(f"🔍 Searching for: '{query}'")
    result = subprocess.run(
        [sys.executable, str(SEARCH_SCRIPT), query],
        capture_output=True, text=True, timeout=30
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

def main():
    print("=" * 50)
    print("🗓️  FRIDAY — Voice-to-Image Reference Tool")
    print("   Say a word or phrase to find reference images")
    print("=" * 50)

    # Check dependencies
    if not LISTEN_SCRIPT.exists():
        print(f"❌ listen.py not found: {LISTEN_SCRIPT}")
        sys.exit(1)
    if not SEARCH_SCRIPT.exists():
        print(f"❌ search script not found: {SEARCH_SCRIPT}")
        sys.exit(1)
    if not shutil.which("feh"):
        print("⚠️  feh not installed. Images will list paths only.")
        print("   Install: sudo dnf install feh")

    # Listen
    query = run_listen()
    if not query:
        print("❌ No query captured. Try again.")
        sys.exit(1)

    # Search
    run_search(query)

    print("\n✅ Done. Say another phrase or Ctrl+C to exit.")

if __name__ == "__main__":
    main()
