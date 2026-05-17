#!/usr/bin/env python3
"""
Friday Config — Shared constants. The 3 working files remain self-contained.
This is for NEW code (friday.py, future voice module) to import.
"""

from pathlib import Path

# Paths
BASE_DIR = Path.home() / "friday"
CORE_DIR = BASE_DIR / "core"
REFS_DIR = BASE_DIR / "refs"
INDEX_DIR = BASE_DIR / "index"

# API
API_CONFIG = BASE_DIR / "api_endpoint.txt"
API_KEY = "lm-studio"
MODEL_NAME = "bartowski/qwen2-vl-2b-instruct"

# Data
INDEX_FILE = BASE_DIR / "captions_multi_lens.json"

# Images
MAX_IMAGE_DIM = 1024
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# Display
WINDOW_TITLE_BASE = "friday-ref"
XP_X = 0
XP_Y = 0
