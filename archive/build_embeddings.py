#!/usr/bin/env python3
"""
Friday Multi-Lens Embedding Builder
Generates CLIP text embeddings for all multi-lens captions.
Run once after indexing. Creates embeddings_multi_lens.npz for semantic search.
"""

import json
import numpy as np
from pathlib import Path

INDEX_FILE = Path.home() / "friday" / "captions_multi_lens.json"
EMBED_FILE = Path.home() / "friday" / "embeddings_multi_lens.npz"

def load_clip():
    try:
        import clip
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        return model, preprocess, device
    except Exception as e:
        print(f"CLIP load failed: {e}")
        print("Install with: pip install git+https://github.com/openai/CLIP.git")
        raise

def main():
    with open(INDEX_FILE) as f:
        index = json.load(f)

    model, preprocess, device = load_clip()

    # Build a flat list of all captions with metadata
    entries = []  # [(filename, lens, caption, embedding)]
    texts = []
    metadata = []

    for filename, data in index.items():
        if "error" in data:
            continue
        captions = data.get("captions", {})
        for lens, caption in captions.items():
            texts.append(caption)
            metadata.append({"file": filename, "lens": lens, "caption": caption})

    print(f"Encoding {len(texts)} captions...")

    # Batch encode
    batch_size = 32
    all_embeddings = []

    import torch
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            tokens = clip.tokenize(batch, truncate=True).to(device)
            embeddings = model.encode_text(tokens)
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
            all_embeddings.append(embeddings.cpu().numpy())
            print(f"  Batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")

    all_embeddings = np.concatenate(all_embeddings, axis=0)

    # Save
    np.savez(
        EMBED_FILE,
        embeddings=all_embeddings,
        metadata=json.dumps(metadata).encode("utf-8")
    )

    print(f"\n✅ Saved {len(texts)} embeddings to {EMBED_FILE}")
    print(f"   Shape: {all_embeddings.shape}")
    print(f"   Files covered: {len(set(m['file'] for m in metadata))}")

if __name__ == "__main__":
    main()
