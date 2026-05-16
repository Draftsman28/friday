#!/usr/bin/env python3
"""
Friday VL Rerank Search - Search with embeddings, then use LLM to rerank by relevance
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

def search_embeddings(query: str, k: int = 10):
    """First pass: fast embedding search"""
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    index = faiss.read_index(str(INDEX_DIR / "vl_text.index"))
    with open(INDEX_DIR / "vl_paths.pkl", "rb") as f:
        paths = pickle.load(f)
    with open(INDEX_DIR / "captions.json", "r") as f:
        captions = json.load(f)

    emb = embed_model.encode(query)
    D, I = index.search(np.array([emb]).astype('float32'), k)

    candidates = []
    for score, idx in zip(D[0], I[0]):
        path = paths[idx]
        candidates.append({
            "path": path,
            "name": Path(path).name,
            "caption": captions.get(path, ""),
            "emb_score": float(score)
        })
    return candidates

def rerank_with_llm(query: str, candidates: list) -> list:
    """Second pass: LLM reranks by true semantic relevance"""

    # Build prompt with candidates
    candidate_text = "\n".join([
        f"[{i+1}] {c['name']}: {c['caption'][:150]}"
        for i, c in enumerate(candidates)
    ])

    payload = {
        "model": "qwen/qwen2.5-vl-7b",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise image relevance judge. Given a search query and image descriptions, rank the images by relevance. Respond ONLY with numbers in order of relevance, like: 3,1,4,2,5"
            },
            {
                "role": "user",
                "content": f'Query: "{query}"\n\nImages:\n{candidate_text}\n\nRank these images by relevance to the query. Most relevant first. Respond ONLY with comma-separated numbers.'
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        ranking_text = data["choices"][0]["message"]["content"].strip()

        # Parse ranking like "3,1,4,2"
        try:
            ranked_indices = [int(x.strip()) - 1 for x in ranking_text.split(",") if x.strip().isdigit()]
            # Reorder candidates
            reranked = []
            for idx in ranked_indices:
                if 0 <= idx < len(candidates):
                    candidates[idx]["llm_rank"] = len(reranked) + 1
                    reranked.append(candidates[idx])
            # Add any missing candidates
            for i, c in enumerate(candidates):
                if i not in ranked_indices:
                    c["llm_rank"] = 99
                    reranked.append(c)
            return reranked[:5]
        except:
            pass
    except Exception as e:
        print(f"  LLM rerank failed: {e}")

    return candidates[:5]

def search(query: str, k: int = 5):
    print(f"Query: '{query}'")
    print("\nPhase 1: Embedding search (fast)...")
    candidates = search_embeddings(query, k=10)
    print(f"  Found {len(candidates)} candidates")

    print("\nPhase 2: LLM rerank (smart)...")
    results = rerank_with_llm(query, candidates)

    print(f"\nTop {len(results)} results (LLM reranked):")
    for i, r in enumerate(results, 1):
        print(f"  #{i} | {r['name']}")
        print(f"      {r['caption'][:100]}...")
        print(f"      emb_score={r['emb_score']:.3f}")
    print()
    return [r["path"] for r in results]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter search query: ")

    search(query)
