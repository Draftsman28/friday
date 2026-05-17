#!/usr/bin/env python3
"""
Friday VL Indexer - Uses local Qwen2.5 VL via LM Studio API to generate rich captions,
then indexes them with lightweight text embeddings for fast search.
"""

import os
import base64
import json
import pickle
from pathlib import Path
import requests
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Config
REF_DIR = Path.home() / "friday/refs"
INDEX_DIR = Path.home() / "friday/index"
INDEX_DIR.mkdir(exist_ok=True)

# LM Studio API endpoint (from your screenshot)
API_URL = "http://10.146.227.21:1234/v1/chat/completions"
API_KEY = "lm-studio"  # LM Studio default

def encode_image(image_path):
    """Encode image to base64 for API"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def caption_image(image_path):
    """Send image to local Qwen VL and get rich description"""
    base64_image = encode_image(image_path)

    # Determine mime type
    ext = Path(image_path).suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/webp"

    payload = {
        "model": "qwen/qwen2.5-vl-7b",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in 2-3 sentences for a visual artist's reference library. Include: subject matter, mood/atmosphere, lighting, dominant colors, composition style. Be concise but specific."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 150
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        caption = data["choices"][0]["message"]["content"].strip()
        return caption
    except Exception as e:
        print(f"  Error captioning {Path(image_path).name}: {e}")
        return ""

def main():
    # Find images
    image_paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.gif"):
        image_paths.extend(REF_DIR.rglob(ext))
    image_paths = [p for p in image_paths if p.is_file()]

    if not image_paths:
        print(f"No images found in {REF_DIR}")
        return

    print(f"Found {len(image_paths)} images. Captioning with Qwen VL (local)...")
    print(f"API: {API_URL}")
    print("This will take a while (~5-15 seconds per image).\n")

    # Generate captions
    captions = {}
    for i, path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] {path.name}...", end=" ", flush=True)
        caption = caption_image(str(path))
        captions[str(path)] = caption
        print(f"OK: {caption[:60]}...")

    # Save captions
    with open(INDEX_DIR / "captions.json", "w") as f:
        json.dump(captions, f, indent=2)
    print(f"\nSaved {len(captions)} captions to captions.json")

    # Build text embedding index (lightweight model, ~20MB)
    print("\nBuilding text embedding index...")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')

    paths_list = list(captions.keys())
    texts = [captions[p] for p in paths_list]

    embeddings = embed_model.encode(texts, show_progress_bar=True)

    dim = len(embeddings[0])
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings).astype('float32'))

    faiss.write_index(index, str(INDEX_DIR / "vl_text.index"))
    with open(INDEX_DIR / "vl_paths.pkl", "wb") as f:
        pickle.dump(paths_list, f)

    print(f"\nDone! Indexed {len(paths_list)} images with VL captions.")
    print(f"Index saved to {INDEX_DIR}")

if __name__ == "__main__":
    main()
