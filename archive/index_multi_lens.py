#!/usr/bin/env python3
"""
Friday Multi-Lens Indexer - Smart persona-based captioning
Each image gets only the lenses that match its detected type.
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
        "prompt": "You are a CHARACTER DESIGNER. Analyze this image for: silhouette readability, proportions, anatomy, costume details, facial expression, hair style, distinctive features. Output ONLY bullet points under these headers. Be concise.",
        "triggers": ["character", "portrait", "face", "person", "figure", "warrior", "idol", "woman", "man", "girl", "boy", "anime"]
    },
    "environment": {
        "prompt": "You are an ENVIRONMENT ARTIST. Analyze this image for: setting type, scale, depth layers, atmospheric perspective, terrain features, weather, time of day. Output ONLY bullet points. Be concise.",
        "triggers": ["landscape", "mountain", "lake", "forest", "city", "street", "room", "sky", "nature", "outdoor", "indoor", "environment"]
    },
    "color": {
        "prompt": "You are a COLORIST. Analyze this image for: dominant palette, color harmony type, temperature, saturation, value range, accent colors, color story. Output ONLY bullet points. Be concise.",
        "triggers": ["color", "palette", "red", "blue", "green", "warm", "cool", "dark", "light", "monochrome", "vibrant", "muted"]
    },
    "motion": {
        "prompt": "You are an ANIMATOR. Analyze this image for: pose dynamics, action lines, implied movement, weight distribution, timing, energy level, gesture. Output ONLY bullet points. Be concise.",
        "triggers": ["action", "dynamic", "fight", "running", "jumping", "pose", "movement", "motion", "dance", "speed", "attack"]
    },
    "composition": {
        "prompt": "You are a COMPOSITION EXPERT. Analyze this image for: framing type, focal point placement, rule of thirds, leading lines, balance, negative space, depth of field. Output ONLY bullet points. Be concise.",
        "triggers": ["composition", "framing", "shot", "close-up", "wide", "angle", "perspective", "layout", "arrangement"]
    },
    "narrative": {
        "prompt": "You are a STORYBOARD ARTIST. Analyze this image for: story moment, emotional beat, character relationship, dramatic tension, before/after implication, narrative function. Output ONLY bullet points. Be concise.",
        "triggers": ["scene", "story", "confrontation", "emotional", "dramatic", "tension", "relationship", "narrative", "plot", "moment"]
    }
}

def detect_image_type(image_path: Path) -> list:
    """Use CLIP to quickly detect image type, then match to lenses"""
    from PIL import Image

    # Quick heuristic: check filename for triggers
    name_lower = image_path.name.lower()
    matched_lenses = set()

    for lens_name, lens_data in LENSES.items():
        for trigger in lens_data["triggers"]:
            if trigger in name_lower:
                matched_lenses.add(lens_name)
                break

    # If no filename match, use CLIP for a quick visual check
    if not matched_lenses:
        try:
            # Load CLIP model briefly for classification
            from transformers import CLIPProcessor, CLIPModel
            model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

            image = Image.open(image_path).convert("RGB")

            # Candidate labels for classification
            labels = [
                "a character portrait", "a landscape environment", 
                "an action scene with movement", "a color palette or mood board",
                "a composition study", "a narrative story moment"
            ]

            inputs = processor(text=labels, images=image, return_tensors="pt", padding=True)
            outputs = model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)

            best_idx = probs.argmax().item()
            lens_map = ["character", "environment", "motion", "color", "composition", "narrative"]
            matched_lenses.add(lens_map[best_idx])

        except Exception:
            # Fallback: apply all lenses
            matched_lenses = set(LENSES.keys())

    # Always include "color" and "composition" as base lenses
    matched_lenses.add("color")
    matched_lenses.add("composition")

    return list(matched_lenses)

def caption_with_lens(image_path: Path, lens_name: str) -> str:
    """Send image to Qwen VL with specific lens prompt"""

    # Read and encode image
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode()

    # Determine mime type
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
                    {"type": "text", "text": "Analyze this image from your professional perspective. Be concise."}
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 300
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
    print("Analyzing each image to detect type and apply matching lenses...\n")

    # Storage
    all_captions = {}  # path -> {lens: caption}
    all_texts = []     # for embedding: "path|lens|caption"
    all_paths = []
    all_lens = []

    for i, path in enumerate(image_paths, 1):
        print(f"[{i}/{len(image_paths)}] {path.name}")

        # Detect which lenses to apply
        lenses = detect_image_type(path)
        print(f"  Detected lenses: {', '.join(lenses)}")

        image_captions = {}

        for lens_name in lenses:
            print(f"  → Captioning with {lens_name} lens...", end=" ", flush=True)
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
