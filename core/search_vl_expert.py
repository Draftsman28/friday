#!/usr/bin/env python3
"""
Friday VL Expert Search - Searches expert art-analysis captions
"""

import sys
import json
import pickle
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

INDEX_DIR = Path.home() / "friday/index"

def search(query: str, k: int = 5):
    print(f"Searching expert captions: '{query}'")

    # Load expert index
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    index = faiss.read_index(str(INDEX_DIR / "vl_expert.index"))
    with open(INDEX_DIR / "vl_expert_paths.pkl", "rb") as f:
        paths = pickle.load(f)

    # Load expert captions
    with open(INDEX_DIR / "captions_expert.json", "r") as f:
        captions = json.load(f)

    # Search
    emb = embed_model.encode(query)
    D, I = index.search(np.array([emb]).astype('float32'), k)

    print(f"\nTop {len(I[0])} results:")
    results = []
    for score, idx in zip(D[0], I[0]):
        path = paths[idx]
        cap = captions.get(path, "")
        print(f"\n  {score:.4f} | {Path(path).name}")
        if cap:
            lines = cap.split("\n")
            for line in lines[:8]:
                if line.strip():
                    print(f"    {line[:90]}")
        results.append(path)
    print()
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter search query: ")

    search(query)
