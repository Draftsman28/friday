#!/usr/bin/env python3
"""
Friday Search — reads LM Studio endpoint from config.
Exact word matching, handles dict captions.
"""

import json
import re
import sys
from pathlib import Path

INDEX_FILE = Path.home() / "friday" / "captions_multi_lens.json"
CONFIG_FILE = Path.home() / "friday" / "api_endpoint.txt"

def get_endpoint():
    if CONFIG_FILE.exists():
        return CONFIG_FILE.read_text().strip()
    return "http://10.146.227.7:1234/v1/chat/completions"

def load_index():
    with open(INDEX_FILE) as f:
        return json.load(f)

def caption_to_str(cap):
    if isinstance(cap, str):
        return cap
    if isinstance(cap, dict):
        parts = []
        for k, v in cap.items():
            if isinstance(v, str):
                parts.append(f"{k}: {v}")
            elif isinstance(v, list):
                parts.append(f"{k}: {', '.join(str(x) for x in v)}")
            else:
                parts.append(f"{k}: {str(v)}")
        return " ".join(parts)
    return str(cap)

def word_match(text, query):
    pattern = r'\b' + re.escape(query.lower()) + r'\b'
    return re.search(pattern, text.lower()) is not None

def search(index, query, lens=None, top_k=5):
    scores = {}
    info = {}
    for filename, entry in index.items():
        if "error" in entry:
            continue
        captions = entry.get("captions", {})
        file_score = 0
        file_matches = []
        for cap_lens, caption in captions.items():
            if lens and lens != "all" and cap_lens != lens:
                continue
            cap_str = caption_to_str(caption)
            if word_match(cap_str, query):
                file_score += 1
                short = cap_str[:80] if len(cap_str) > 80 else cap_str
                file_matches.append((cap_lens, short, query))
        if file_score > 0:
            scores[filename] = file_score
            info[filename] = file_matches
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k], info

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--lens", default="all")
    parser.add_argument("-k", "--top", type=int, default=5)
    args = parser.parse_args()
    index = load_index()
    results, info = search(index, args.query, args.lens, args.top)
    if not results:
        print(f"NO_RESULTS:{args.query}")
        return
    for rank, (filename, score) in enumerate(results, 1):
        entry = index[filename]
        lenses = entry.get("lenses", [])
        print(f"{rank}. {filename} | score:{score} | lenses:{','.join(lenses)}")
        for cap_lens, short, term in info.get(filename, [])[:2]:
            print(f"   [{cap_lens}] {short}... (match:{term})")

if __name__ == "__main__":
    main()
