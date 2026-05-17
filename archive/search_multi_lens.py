#!/usr/bin/env python3
"""
Friday Multi-Lens Search
Searches captions_multi_lens.json by lens or across all.
Opens results with feh (or imv as fallback).
"""

import json
import sys
import subprocess
import argparse
from pathlib import Path

INDEX_FILE = Path.home() / "friday" / "captions_multi_lens.json"
IMAGE_DIR = Path.home() / "friday" / "refs"

def load_index():
    if not INDEX_FILE.exists():
        print(f"Index not found: {INDEX_FILE}")
        print("Run the indexer first.")
        sys.exit(1)
    with open(INDEX_FILE) as f:
        return json.load(f)

def search(index, query, lens=None, top_k=5):
    """Simple keyword search. Case-insensitive."""
    query = query.lower()
    scores = []

    for filename, entry in index.items():
        if "error" in entry:
            continue

        captions = entry.get("captions", {})

        if lens == "all" or lens is None:
            # Search across all captions + master
            text = " ".join(captions.values()).lower()
        elif lens == "master":
            # Search a combined master caption
            text = " ".join(captions.values()).lower()
        else:
            # Search specific lens
            text = captions.get(lens, "").lower()

        # Simple scoring: count query word matches
        score = sum(1 for word in query.split() if word in text)
        if score > 0:
            scores.append((score, filename, entry))

    scores.sort(reverse=True)
    return scores[:top_k]

def open_images(filenames):
    paths = [str(IMAGE_DIR / f) for f in filenames]

    # Try feh first, then imv
    for viewer in ["feh", "imv"]:
        try:
            subprocess.run([viewer, "-Z", "-F"] + paths, check=False)
            return
        except FileNotFoundError:
            continue

    print("No image viewer found (tried: feh, imv)")
    print("Files:")
    for p in paths:
        print(f"  {p}")

def main():
    parser = argparse.ArgumentParser(description="Search Friday multi-lens index")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--lens", default="all",
                        help="Lens to search: character, environment, color, motion, composition, narrative, all, master")
    parser.add_argument("-k", "--top", type=int, default=5, help="Number of results")
    parser.add_argument("--no-open", action="store_true", help="Don't open images, just list")
    args = parser.parse_args()

    index = load_index()
    results = search(index, args.query, args.lens, args.top)

    if not results:
        print(f"No results for '{args.query}' (lens: {args.lens})")
        return

    print(f"\n🔍 Query: '{args.query}' | Lens: {args.lens} | Top {len(results)} results\n")
    filenames = []

    for rank, (score, filename, entry) in enumerate(results, 1):
        filenames.append(filename)
        lenses = entry.get("lenses", [])
        captions = entry.get("captions", {})

        print(f"{rank}. {filename} (score: {score})")
        print(f"   Lenses: {', '.join(lenses)}")

        # Show the relevant caption(s)
        if args.lens in captions:
            print(f"   [{args.lens}] {captions[args.lens][:120]}...")
        elif args.lens in ("all", "master"):
            for ln, cap in captions.items():
                if any(w in cap.lower() for w in args.query.lower().split()):
                    print(f"   [{ln}] {cap[:120]}...")
        print()

    if not args.no_open:
        open_images(filenames)

if __name__ == "__main__":
    main()
