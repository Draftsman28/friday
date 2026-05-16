#!/usr/bin/env python3
import sys
import pickle
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

INDEX_DIR = Path.home() / "friday/index"

def search(query: str, k: int = 5):
    print(f"Searching: '{query}'")

    # Load index
    model = SentenceTransformer('clip-ViT-B-32')
    index = faiss.read_index(str(INDEX_DIR / "images.index"))
    with open(INDEX_DIR / "paths.pkl", "rb") as f:
        paths = pickle.load(f)

    # Search
    emb = model.encode(query)
    D, I = index.search(np.array([emb]).astype('float32'), k)

    # Print results
    print(f"\nTop {len(I[0])} results:")
    for score, idx in zip(D[0], I[0]):
        path = paths[idx]
        print(f"  {score:.4f} | {Path(path).name}")
    print()

    # Return full paths for other scripts
    return [paths[i] for i in I[0]]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter search query: ")

    search(query)