#!/usr/bin/env python3
"""
Friday Multi-Lens Indexer - LM Studio ONLY version
No extra downloads. Uses your local Qwen VL for everything.
"""

import os
import json
import base64
import pickle
import requests
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# --- CONFIG ---
REF_DIR = Path.home() / "friday/refs"
INDEX_DIR = Path.home() / "friday/index"
INDEX_DIR.mkdir(exist_ok=True)
API_URL = "http://10.146.227.181:1234/v1/chat/completions"

# --- LENS DEFINITIONS ---
LENSES = {
    "character": {
        "prompt": "You are a CHARACTER DESIGNER. Analyze this image for: silhouette readability, proportions, anatomy, costume details, facial expression, hair style, distinctive features. Output ONLY bullet points under these headers. Be concise. 3-4 sentences max.",
        "keywords": ["character", "portrait", "face", "person", "figure", "warrior", "idol", "woman", "man", "girl", "boy", "anime", "hero", "villain"]
    },
    "environment": {
        "prompt": "You are an ENVIRONMENT ARTIST. Analyze this image for: setting type, scale, depth layers, atmospheric perspective, terrain features, weather, time of day. Output ONLY bullet points. Be concise. 3-4 sentences max.",
        "keywords": ["landscape", "mountain", "lake", "forest", "city", "street", "room", "sky", "nature", "outdoor", "indoor", "environment", "building"]
    },
    "color": {
        "prompt": "You are a COLORIST. Analyze this image for: dominant palette, color harmony type, temperature, saturation, value range, accent colors, color story. Output ONLY bullet points. Be concise. 3-4 sentences max.",
        "keywords": ["color", "palette", "red", "blue", "green", "warm", "cool", "dark", "light", "monochrome", "vibrant", "muted", "tone"]
    },
    "motion": {
        "prompt": "You are an ANIMATOR. Analyze this image for: pose dynamics, action lines, implied movement, weight distribution, timing, energy level, gesture. Output ONLY bullet points. Be concise. 3-4 sentences max.",
        "keywords": ["action", "dynamic", "fight", "running", "jumping", "pose", "movement", "motion", "dance", "speed", "attack", "battle"]
    },
    "composition": {
        "prompt": "You are a COMPOSITION EXPERT. Analyze this image for: framing type, focal point placement, rule of thirds, leading lines, balance, negative space, depth of field. Output ONLY bullet points. Be concise. 3-4 sentences max.",
        "keywords": ["composition", "framing", "shot", "close-up", "wide", "angle", "perspective", "layout", "arrangement"]
    },
    "narrative": {
        "prompt": "You are a STORYBOARD ARTIST. Analyze this image for: story moment, emotional beat, character relationship, dramatic tension, before/after implication, narrative function. Output ONLY bullet points. Be concise. 3-4 sentences max.",
        "keywords": ["scene", "story", "confrontation", "emotional", "dramatic", "tension", "relationship", "narrative", "plot", "moment"]
    }
}

def detect_type_with_qwen(image_path: Path) -> list:
    """Use Qwen VL to detect image type, then match to lenses"""

    with open(image_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode()

    ext = image_path.suffix.lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png" if ext == ".png" else "image/webp"

    # Quick classification prompt
    payload = {
        "model": "qwen/qwen2.5-vl-7b",
        "messages": [
            {
                "role": "system",
                "content": "You are an image classifier. Look at this image and classify it into 1-3 categories from this list: character, environment, color, motion, composition, narrative. Respond ONLY with the category names, comma-separated. Example: 'character, color, composition'"
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text", "text": "Classify this image."}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        result = data["choices"][0]["message"]["content"].strip().lower()

        # Parse categories from response
        matched = []
        for lens_name in LENSES.keys():
            if lens_name in result:
                matched.append(lens_name)

        # Always include color and composition
        if "color" not in matched:
            matched.append("color")
        if "composition" not in matched:
            matched.append("composition")

        return matched if matched else ["character", "color", "composition"]

    except Exception as e:
        print(f"  Qwen detection failed: {e}, using filename fallback")
        return detect_from_filename(image_path)

def detect_from_filename(image_path: Path) -> list:
    """Fallback: detect from filename keywords"""
    name_lower = image_path.name.lower()
    matched = []

    for lens_name, lens_data in LENSES.items():
        for keyword in lens_data["keywords"]:
            if keyword in name_lower:
                matched.append(lens_name)
                break

    # Always include color and composition
    if "color" not in matched:
        matched.append("color")
    if "composition" not in matched:
        matched.append("composition")

    return matched if matched else ["character", "color", "composition"]

def caption_with_lens(image_path: Path, lens_name: str) -> str:
    """Send image to Qwen VL with specific lens prompt"""

    with open(image_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode()

    ext = image_path.suffix.lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png" if ext == ".png" else "image/webp"

    lens = LENSES[lens_name]

    payload = {
        "model": "qwen/qwen2.5-vl-7b",
        "messages": [
            {
                "role": "system",
                "content": lens["prompt"]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text", "text": "Analyze this image from your professional perspective."}
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[ERROR: {str(e)[:50]}]"

def build_multi_lens_index():
    """Main indexing function"""

    # Find images
    image_paths = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        image_paths.extend(REF_DIR.rglob(ext))
    image_paths = sorted([p for p in image_paths if p.is_file()])

    if not image_paths:
        print("No images found.")
        return

    print(f"Found {len(image_paths)} images.")
    print("Using LM Studio ONLY. No extra model downloads.\n")

    # Storage
    all_captions = {}
    all_texts = []
    all_paths = []
    all_lens = []

    for i, path in enumerate(image_paths, 1):
        print(f"[{i}/{len(image_paths)}] {path.name}")

        # Detect lenses using Qwen or filename
        lenses = detect_type_with_qwen(path)
        print(f"  Detected lenses: {', '.join(lenses)}")

        image_captions = {}

        for lens_name in lenses:
            print(f"  → {lens_name}...", end=" ", flush=True)
            caption = caption_with_lens(path, lens_name)
            image_captions[lens_name] = caption

            # Store for embedding
            all_texts.append(f"{path.name} [{lens_name}]: {caption}")
            all_paths.append(str(path))
            all_lens.append(lens_name)

            print(f"OK ({len(caption)} chars)")

        all_captions[str(path)] = image_captions
        print()

    # Save captions
    with open(INDEX_DIR / "multi_lens_captions.json", "w") as f:
        json.dump(all_captions, f, indent=2)

    print(f"\nSaved {len(all_captions)} multi-lens caption sets.")

    # Build embeddings
    print("\nBuilding text embedding index...")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = embed_model.encode(all_texts, show_progress_bar=True)

    dim = len(embeddings[0])
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings).astype('float32'))

    faiss.write_index(index, str(INDEX_DIR / "multi_lens.index"))

    with open(INDEX_DIR / "multi_lens_meta.pkl", "wb") as f:
        pickle.dump({"paths": all_paths, "lenses": all_lens, "texts": all_texts}, f)

    print(f"\nDone! Indexed {len(all_texts)} lens-specific captions.")
    print(f"Index saved to: {INDEX_DIR}")
    print(f"\nLens distribution:")
    from collections import Counter
    for lens, count in Counter(all_lens).most_common():
        print(f"  {lens}: {count} captions")

if __name__ == "__main__":
    build_multi_lens_index()
