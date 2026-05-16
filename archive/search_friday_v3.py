#!/usr/bin/env python3
"""
Friday Search v3 — Substring Matching on Plain-Text Captions
==============================================================
No regex word boundaries. No exact matching.
Just substring search across CHARACTER + ENVIRONMENT + COLOR.
"""

import sys
import json
import re
from pathlib import Path

INDEX_FILE = Path.home() / "friday/captions_plain.json"
REF_DIR = Path.home() / "friday/refs"

def search(query, k=5):
    if not INDEX_FILE.exists():
        print("No index found. Run reindex_all_v3.py first.")
        return []

    with open(INDEX_FILE) as f:
        index = json.load(f)

    query = query.lower().strip()
    query_words = query.split()

    results = []
    for name, captions in index.items():
        # Combine all caption fields into one searchable text
        full_text = " ".join([
            captions.get("character", ""),
            captions.get("environment", ""),
            captions.get("color", "")
        ]).lower()

        # Score: how many query words appear as substrings?
        score = sum(1 for word in query_words if word in full_text)

        if score > 0:
            results.append((score, name, captions))

    # Sort by score (descending), then by name
    results.sort(key=lambda x: (-x[0], x[1]))

    print(f"Query: '{query}' — {len(results)} matches\n")
    for score, name, caps in results[:k]:
        print(f"  [{score} hits] {name}")
        print(f"    CHARACTER: {caps.get('character', 'N/A')[:80]}")
        print(f"    ENVIRONMENT: {caps.get('environment', 'N/A')[:80]}")
        print(f"    COLOR: {caps.get('color', 'N/A')[:80]}")
        print()

    return [REF_DIR / name for score, name, caps in results[:k]]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Search: ")

    search(query)
