#!/usr/bin/env python3
"""
Friday Multi-Lens Semantic Search
Uses CLIP text embeddings for meaning-based search across captions.
Opens results with feh, imv, or xdg-open.
"""

import json
import sys
import subprocess
import shutil
import argparse
import numpy as np
from pathlib import Path

INDEX_FILE = Path.home() / "friday" / "captions_multi_lens.json"
EMBED_FILE = Path.home() / "friday" / "embeddings_multi_lens.npz"
IMAGE_DIR = Path.home() / "friday" / "refs"

def load_clip():
    import clip
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    return model, device

def load_embeddings():
    if not EMBED_FILE.exists():
        print(f"Embeddings not found: {EMBED_FILE}")
        print("Run: python ~/friday/core/build_embeddings.py")
        sys.exit(1)
    data = np.load(EMBED_FILE)
    embeddings = data["embeddings"]
    metadata = json.loads(data["metadata"].item())
    return embeddings, metadata

def embed_query(model, device, query):
    import torch
    with torch.no_grad():
        tokens = clip.tokenize([query], truncate=True).to(device)
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        return embedding.cpu().numpy()[0]

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search(embeddings, metadata, query_embedding, lens=None, top_k=5):
    scores = []
    for i, meta in enumerate(metadata):
        if lens and lens != "all" and lens != "master":
            if meta["lens"] != lens:
                continue
        sim = cosine_similarity(query_embedding, embeddings[i])
        scores.append((sim, meta))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_k]

def open_images(filenames):
    paths = [str(IMAGE_DIR / f) for f in filenames]

    # Try multiple viewers
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
            except Exception as e:
                print(f"   ⚠️  {viewer} failed: {e}")
                continue

    print("   ⚠️  No image viewer found. Files:")
    for p in paths:
        print(f"      {p}")

def main():
    parser = argparse.ArgumentParser(description="Semantic search Friday multi-lens index")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--lens", default="all",
                        help="Lens filter: character, environment, color, motion, composition, narrative, all, master")
    parser.add_argument("-k", "--top", type=int, default=5, help="Number of results")
    parser.add_argument("--no-open", action="store_true", help="Don't open images")
    args = parser.parse_args()

    print(f"\n🔍 Loading CLIP model...")
    model, device = load_clip()

    print(f"📦 Loading embeddings...")
    embeddings, metadata = load_embeddings()

    print(f"🧠 Encoding query: '{args.query}'...")
    query_embedding = embed_query(model, device, args.query)

    results = search(embeddings, metadata, query_embedding, args.lens, args.top)

    if not results:
        print(f"\nNo results for '{args.query}' (lens: {args.lens})")
        return

    print(f"\n🔍 Query: '{args.query}' | Lens: {args.lens} | Top {len(results)} results\n")

    # Group by filename
    seen_files = []
    for rank, (score, meta) in enumerate(results, 1):
        filename = meta["file"]
        if filename not in seen_files:
            seen_files.append(filename)

        print(f"{rank}. {filename} | {meta['lens']} | score: {score:.3f}")
        print(f"   {meta['caption'][:120]}...")
        print()

    if not args.no_open and seen_files:
        open_images(seen_files[:args.top])

if __name__ == "__main__":
    import clip
    import torch
    main()
