#!/usr/bin/env python3
import os
from pathlib import Path
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Paths
REF_DIR = Path.home() / "friday/refs"
INDEX_DIR = Path.home() / "friday/index"
INDEX_DIR.mkdir(exist_ok=True)

# Load model (CLIP, CPU-only, ~150MB)
print("Loading CLIP model...")
model = SentenceTransformer('clip-ViT-B-32')

# Find images
image_paths = []
for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.gif"):
    image_paths.extend(REF_DIR.rglob(ext))
image_paths = [p for p in image_paths if p.is_file()]

if not image_paths:
    print(f"No images found in {REF_DIR}")
    exit(1)

print(f"Found {len(image_paths)} images. Indexing...")

# Build embeddings
embeddings = []
for i, path in enumerate(image_paths):
    print(f"  [{i+1}/{len(image_paths)}] {path.name}")
    emb = model.encode(str(path))
    embeddings.append(emb)

# Create FAISS index
dim = len(embeddings[0])
index = faiss.IndexFlatIP(dim)  # Inner product = cosine for normalized CLIP
index.add(np.array(embeddings).astype('float32'))

# Save
faiss.write_index(index, str(INDEX_DIR / "images.index"))
with open(INDEX_DIR / "paths.pkl", "wb") as f:
    pickle.dump([str(p) for p in image_paths], f)

print(f"\nDone. Indexed {len(image_paths)} images.")
print(f"Index saved to: {INDEX_DIR}")