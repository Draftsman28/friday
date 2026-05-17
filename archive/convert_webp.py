#!/usr/bin/env python3
"""
Friday WebP Converter - Converts webp files to jpg and moves originals to temp folder
"""

import os
import shutil
import subprocess
from pathlib import Path

REF_DIR = Path.home() / "friday/refs"
TEMP_DIR = Path.home() / "friday/temp_webp"

def convert_webp():
    # Create temp folder
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Find all webp files
    webp_files = list(REF_DIR.glob("*.webp"))

    if not webp_files:
        print("No webp files found.")
        return

    print(f"Found {len(webp_files)} webp files.")

    for webp_path in webp_files:
        jpg_name = webp_path.stem + ".jpg"
        jpg_path = REF_DIR / jpg_name
        temp_webp_path = TEMP_DIR / webp_path.name

        # Convert to jpg using ffmpeg
        print(f"Converting: {webp_path.name} -> {jpg_name}")
        result = subprocess.run(
            ["ffmpeg", "-i", str(webp_path), "-frames:v", "1", str(jpg_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and jpg_path.exists():
            # Move original webp to temp
            shutil.move(str(webp_path), str(temp_webp_path))
            print(f"  ✓ Converted. Original moved to: {temp_webp_path}")
        else:
            print(f"  ✗ Failed to convert {webp_path.name}")
            if jpg_path.exists():
                jpg_path.unlink()

    print(f"
Done. Original webp files are in: {TEMP_DIR}")
    print(f"Converted jpg files are in: {REF_DIR}")

if __name__ == "__main__":
    convert_webp()
