#!/usr/bin/env python3
"""
Friday Domain Survey
Shows all images with current captions so you can pick domains.
"""

import json
from pathlib import Path

INDEX_FILE = Path.home() / "friday" / "captions_multi_lens.json"
IMAGE_DIR = Path.home() / "friday" / "refs"

def main():
    if not INDEX_FILE.exists():
        print(f"No index found: {INDEX_FILE}")
        return

    with open(INDEX_FILE) as f:
        index = json.load(f)

    print("\n📋 CURRENT INDEX — ALL IMAGES\n")
    print("=" * 60)

    for filename in sorted(index.keys()):
        entry = index[filename]
        if "error" in entry:
            print(f"\n❌ {filename} — ERROR: {entry['error']}")
            continue

        lenses = entry.get("lenses", [])
        captions = entry.get("captions", {})

        print(f"\n🖼️  {filename}")
        print(f"   Lenses: {', '.join(lenses)}")
        for ln, cap in captions.items():
            print(f"   [{ln}] {cap}")

    print("\n" + "=" * 60)
    print("\nSUGGESTED DOMAINS:")
    print("   combat      → training, fights, warriors, swords, action")
    print("   portrait    → faces, characters, emotional close-ups")
    print("   atmosphere  → environments, lighting, weather, mood")
    print("   anime       → stylized, graphic, Mind Game style")
    print("\nTo re-index a domain:")
    print("   python ~/friday/core/index_targeted.py --domain combat --files img1.jpg img2.jpg")
    print("\nTo re-index ALL images in a domain (auto-detect not yet supported, list files):")
    print("   python ~/friday/core/index_targeted.py --domain combat --files *.jpg")

if __name__ == "__main__":
    main()
