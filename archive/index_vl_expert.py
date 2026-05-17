#!/usr/bin/env python3
"""
Friday VL Expert Indexer - Uses local Qwen VL via LM Studio API to generate 
art-field-expert captions focused on visual analysis, technique, and creative use.
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

# Paths
REF_DIR = Path.home() / "friday/refs"
INDEX_DIR = Path.home() / "friday/index"
INDEX_DIR.mkdir(exist_ok=True)

# LM Studio API endpoint
API_URL = "http://10.146.227.181:1234/v1/chat/completions"
API_KEY = "lm-studio"

def encode_image(image_path):
    """Encode image to base64 for API"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def caption_image_expert(image_path):
    """Send image to local Qwen VL and get EXPERT art analysis"""
    base64_image = encode_image(image_path)

    # Determine mime type
    ext = Path(image_path).suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/webp"

    # EXPERT PROMPT - Art field professional perspective
    expert_prompt = """You are a senior visual development artist and art director with 20 years experience in animation, concept art, and illustration. Analyze this reference image from a WORKING ARTIST's perspective.

Provide a structured analysis covering:

1. SUBJECT & NARRATIVE: What is depicted? What story or mood does it convey?

2. COLOR PALETTE: Dominant colors, color harmony (complementary/analogous/monochromatic), saturation levels, temperature (warm/cool/neutral)

3. LIGHTING: Light source direction, quality (hard/soft/diffused), time of day feel, chiaroscuro level, atmospheric perspective

4. COMPOSITION: Framing (close/medium/wide), focal point, rule of thirds, symmetry/asymmetry, leading lines, depth layers

5. STYLE & TECHNIQUE: Art style (anime, realism, impressionist, etc), line quality, brushwork texture, rendering approach, reference era or artist influence

6. EMOTIONAL TONE: The feeling it evokes - melancholic, energetic, mysterious, nostalgic, etc

7. PRACTICAL USE: What kind of project would this serve? (character design, environment painting, color key, mood board, anatomy study, lighting reference)

Be concise but specific. Use art terminology. This caption will be used to SEARCH a reference library, so include every descriptive detail a visual artist might query for."""

    payload = {
        "model": "qwen/qwen2.5-vl-7b",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": expert_prompt
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
        "max_tokens": 400
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

    print(f"Found {len(image_paths)} images. Captioning with EXPERT art analysis (local)...")
    print(f"API: {API_URL}")
    print("This will take longer (~10-20 seconds per image) but produces rich artist-level captions.\n")

    # Generate expert captions
    captions = {}
    for i, path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] {path.name}...", end=" ", flush=True)
        caption = caption_image_expert(str(path))
        captions[str(path)] = caption
        preview = caption[:80].replace("\n", " ") if caption else "FAILED"
        print(f"OK: {preview}...")

    # Save captions
    with open(INDEX_DIR / "captions_expert.json", "w") as f:
        json.dump(captions, f, indent=2)
    print(f"\nSaved {len(captions)} expert captions to captions_expert.json")

    # Build text embedding index
    print("\nBuilding text embedding index...")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')

    paths_list = list(captions.keys())
    texts = [captions[p] for p in paths_list]

    embeddings = embed_model.encode(texts, show_progress_bar=True)

    dim = len(embeddings[0])
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings).astype('float32'))

    faiss.write_index(index, str(INDEX_DIR / "vl_expert.index"))
    with open(INDEX_DIR / "vl_expert_paths.pkl", "wb") as f:
        pickle.dump(paths_list, f)

    print(f"\nDone! Indexed {len(paths_list)} images with EXPERT art analysis.")
    print(f"Index saved to {INDEX_DIR}")

if __name__ == "__main__":
    main()
