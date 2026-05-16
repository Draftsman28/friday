#!/usr/bin/env python3
"""
Friday VL Smart Search - Uses local Qwen VL LLM to understand and expand queries
before searching caption embeddings.
"""

import sys
import json
import pickle
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import requests

INDEX_DIR = Path.home() / "friday/index"
API_URL = "http://10.146.227.181:1234/v1/chat/completions"

def expand_query_with_llm(user_query: str) -> str:
    """Use local Qwen LLM to expand and enrich the search query"""
    
    payload = {
        "model": "qwen/qwen2.5-vl-7b",
        "messages": [
            {
                "role": "system",
                "content": "You are a creative reference librarian. Your job is to expand a visual artist's search query into rich descriptive terms that will match image captions. Output ONLY the expanded search terms - no explanations, no markdown, just comma-separated descriptive keywords and phrases."
            },
            {
                "role": "user",
                "content": f'Expand this search query into rich visual descriptive terms for searching an image reference library: "{user_query}"'
            }
        ],
        "temperature": 0.4,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        expanded = data["choices"][0]["message"]["content"].strip()
        # Clean up - remove markdown, quotes, explanations
        expanded = expanded.replace("**", "").replace("*", "")
        expanded = expanded.replace('"', "").replace("'", "")
        # Take first line if multiple lines
        expanded = expanded.split("\n")[0].strip()
        return expanded
    except Exception as e:
        print(f"  LLM expansion failed: {e}")
        return user_query

def search(query: str, k: int = 5, use_llm: bool = True):
    print(f"Original query: '{query}'")
    
    # Expand query with LLM
    if use_llm:
        print("Expanding with local LLM...", end=" ", flush=True)
        expanded_query = expand_query_with_llm(query)
        print(f"Done.")
        print(f"Expanded: '{expanded_query}'")
        search_text = f"{query} {expanded_query}"
    else:
        search_text = query
    
    # Load index
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    index = faiss.read_index(str(INDEX_DIR / "vl_text.index"))
    with open(INDEX_DIR / "vl_paths.pkl", "rb") as f:
        paths = pickle.load(f)
    
    # Load captions
    with open(INDEX_DIR / "captions.json", "r") as f:
        captions = json.load(f)
    
    # Search
    emb = embed_model.encode(search_text)
    D, I = index.search(np.array([emb]).astype('float32'), k)
    
    print(f"\nTop {len(I[0])} results:")
    results = []
    for score, idx in zip(D[0], I[0]):
        path = paths[idx]
        cap = captions.get(path, "")
        print(f"  {score:.4f} | {Path(path).name}")
        if cap:
            print(f"         {cap[:100]}...")
        results.append(path)
    print()
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter search query: ")
    
    # Check for --no-llm flag
    use_llm = True
    if "--no-llm" in sys.argv:
        use_llm = False
        sys.argv.remove("--no-llm")
        query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else query
    
    search(query, use_llm=use_llm)
