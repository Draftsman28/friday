#!/usr/bin/env python3
"""
Friday Multi-Lens Search with LLM Query Expansion
Uses your existing Qwen2 VL 2B in LM Studio for semantic understanding.
1 API call per search → expands query → keyword matches across all captions.
No CLIP. No new dependencies.
"""

import json
import sys
import subprocess
import shutil
import urllib.request
import urllib.error
import argparse
from pathlib import Path

INDEX_FILE = Path.home() / "friday" / "captions_multi_lens.json"
IMAGE_DIR = Path.home() / "friday" / "refs"
API_URL = "http://10.146.227.181:1234/v1/chat/completions"
API_KEY = "lm-studio"
MODEL_NAME = "bartowski/qwen2-vl-2b-instruct"

def load_index():
    if not INDEX_FILE.exists():
        print(f"Index not found: {INDEX_FILE}")
        sys.exit(1)
    with open(INDEX_FILE) as f:
        return json.load(f)

def expand_query(query):
    """Ask LLM to expand query into related search terms."""
    prompt = f"""You are a search assistant for a visual art reference library.
Given a user's search query, output ONLY a JSON array of 8-12 related search terms and synonyms.
Include the original query, broader concepts, narrower concepts, and emotionally related terms.

Query: "{query}"

Output format: ["term1", "term2", "term3", ...]
Rules:
- Output ONLY the JSON array. No explanations. No markdown fences.
- Terms should be single words or short phrases (1-3 words max).
- Include the original query as the first term."""

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 200
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data["choices"][0]["message"]["content"]

            # Strip markdown
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```json")[-1].split("```")[0].strip()
            elif raw.startswith("```"):
                raw = raw[3:].strip()
                if raw.endswith("```"):
                    raw = raw[:-3].strip()

            terms = json.loads(raw)
            if isinstance(terms, list):
                return [t.lower() for t in terms if isinstance(t, str)]
            return [query.lower()]
    except Exception as e:
        print(f"   ⚠️  Query expansion failed: {e}")
        return [query.lower()]

def search(index, terms, lens=None, top_k=5):
    """Search captions for any of the expanded terms."""
    scores = {}  # filename -> score
    matches = {}  # filename -> [(lens, caption, matched_term)]

    for filename, entry in index.items():
        if "error" in entry:
            continue

        captions = entry.get("captions", {})
        file_score = 0
        file_matches = []

        for cap_lens, caption in captions.items():
            if lens and lens != "all" and lens != "master" and cap_lens != lens:
                continue

            cap_lower = caption.lower()
            for term in terms:
                if term in cap_lower:
                    file_score += 1
                    file_matches.append((cap_lens, caption, term))

        if file_score > 0:
            scores[filename] = file_score
            matches[filename] = file_matches

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k], matches

def open_images(filenames):
    paths = [str(IMAGE_DIR / f) for f in filenames]

    for viewer_cmd in [
        ["feh", "-Z", "-F"] + paths,
        ["imv"] + paths,
        ["xdg-open"] + paths,
    ]:
        viewer = viewer_cmd[0]
        if shutil.which(viewer):
            try:
                subprocess.Popen(viewer_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"   🖼️  Opened with {viewer}")
                return
            except Exception:
                continue

    print("   ⚠️  No image viewer found. Files:")
    for p in paths:
        print(f"      {p}")

def main():
    parser = argparse.ArgumentParser(description="LLM-expanded search for Friday")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--lens", default="all",
                        help="Lens filter: character, environment, color, motion, composition, narrative, all, master")
    parser.add_argument("-k", "--top", type=int, default=5, help="Number of results")
    parser.add_argument("--no-expand", action="store_true", help="Skip LLM expansion, use raw query only")
    parser.add_argument("--no-open", action="store_true", help="Don't open images")
    args = parser.parse_args()

    index = load_index()

    if args.no_expand:
        terms = [args.query.lower()]
        print(f"🔍 Raw query: '{args.query}' | Lens: {args.lens}")
    else:
        print(f"🔍 Expanding query: '{args.query}'...")
        terms = expand_query(args.query)
        print(f"   🧠 Expanded to: {terms}")

    results, matches = search(index, terms, args.lens, args.top)

    if not results:
        print(f"\nNo results for '{args.query}' (lens: {args.lens})")
        return

    print(f"\n🔍 Top {len(results)} results:\n")
    filenames = []

    for rank, (filename, score) in enumerate(results, 1):
        filenames.append(filename)
        entry = index[filename]
        lenses = entry.get("lenses", [])

        print(f"{rank}. {filename} (matches: {score})")
        print(f"   Lenses: {', '.join(lenses)}")

        # Show matched captions
        for cap_lens, caption, term in matches.get(filename, [])[:3]:
            print(f"   [{cap_lens}] {caption[:100]}... (matched: '{term}')")
        print()

    if not args.no_open and filenames:
        open_images(filenames)

if __name__ == "__main__":
    main()
