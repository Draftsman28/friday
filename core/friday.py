#!/usr/bin/env python3
"""
Friday — Main entry point.
Thin wrapper around friday_text.py. Voice input will be added here (Goal B).
"""

import sys

# Ensure core/ is importable when run from anywhere
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import friday_text

if __name__ == "__main__":
    friday_text.main()
