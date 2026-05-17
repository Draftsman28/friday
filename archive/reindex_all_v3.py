#!/usr/bin/env python3
"""
Friday ReIndexer v3 — Bulletproof Plain-Text Captioning
=======================================================
NO JSON. NO MARKDOWN. NO STRUCTURED OUTPUT.
Just plain text with rigid line prefixes that the model CAN follow.

Based on research: Qwen2 VL 2B hallucinates JSON but writes beautiful plain text.
"""

import os
import re
import json
import base64
import time
from pathlib import Path
from PIL import Image
import requests

# ── CONFIG ──────────────────────────────────────────────────────────
REF_DIR = Path.home() / "friday/refs"
INDEX_FILE = Path.home() / "friday/captions_plain.json"
API_FILE = Path.home() / "friday/api_endpoint.txt"
MAX_SIZE = 1024

# ── PROMPT (Plain text only — no JSON, no examples to copy) ───────────
CAPTION_PROMPT = """Describe this image in exactly 3 short sentences.

CHARACTER: [the main subject — person, creature, object, or "none"]
ENVIRONMENT: [the setting, mood, atmosphere, or "none"]
COLOR: [dominant colors, lighting quality, palette, or "none"]

Rules:
- Each line MUST start with the prefix shown (CHARACTER:, ENVIRONMENT:, COLOR:)
- Keep each description under 25 words
- Be specific and visual — use words an artist would search for
- If a category doesn't apply, write "none"
- Do NOT use markdown, code blocks, or JSON
- Do NOT copy these instructions — write about the image only"""

# ── API SETUP ─────────────────────────────────────────────────────────
def get_api_url():
    if API_FILE.exists():
        url = API_FILE.read_text().strip()
        if url:
            return url
    # Auto-detect
    import subprocess
    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
    ips = result.stdout.strip().split()
    for ip in ips:
        test_url = f"http://{ip}:1234/v1/chat/completions"
        try:
            r = requests.get(test_url.replace('/v1/chat/completions', '/v1/models'), timeout=2)
            if r.status_code == 200:
                API_FILE.write_text(test_url)
                return test_url
        except:
            continue
    return "http://localhost:1234/v1/chat/completions"

API_URL = get_api_url()

# ── IMAGE ENCODING ────────────────────────────────────────────────────
def encode_image(path):
    img = Image.open(path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    w, h = img.size
    if max(w, h) > MAX_SIZE:
        ratio = MAX_SIZE / max(w, h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
    import io
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return base64.b64encode(buf.getvalue()).decode()

# ── PLAIN-TEXT PARSER (Bulletproof) ──────────────────────────────────
def parse_plaintext(response_text):
    """Parse CHARACTER/ENVIRONMENT/COLOR lines. Handles markdown wrappers."""
    # Strip markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first ```json or ``` line and last ``` line
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    result = {"character": "", "environment": "", "color": ""}
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("CHARACTER:"):
            result["character"] = line.replace("CHARACTER:", "").strip()
        elif line.startswith("ENVIRONMENT:"):
            result["environment"] = line.replace("ENVIRONMENT:", "").strip()
        elif line.startswith("COLOR:"):
            result["color"] = line.replace("COLOR:", "").strip()

    # Validation: at least one field must be non-empty
    if not any(result.values()):
        return None
    return result

# ── CAPTION ONE IMAGE ───────────────────────────────────────────────
def caption_image(path):
    b64 = encode_image(path)
    payload = {
        "model": "bartowski/qwen2-vl-2b-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": CAPTION_PROMPT}
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }

    try:
        r = requests.post(API_URL, json=payload, timeout=60)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        parsed = parse_plaintext(text)
        return parsed, text
    except Exception as e:
        return None, str(e)

# ── MAIN ────────────────────────────────────────────────────────────
def main():
    images = sorted([p for p in REF_DIR.iterdir() 
                      if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp','.bmp')])

    # Load existing index
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            index = json.load(f)
    else:
        index = {}

    print(f"Friday ReIndexer v3 — Plain Text Mode")
    print(f"API: {API_URL}")
    print(f"Images: {len(images)} found\n")

    success = 0
    failed = []

    for i, path in enumerate(images, 1):
        name = path.name
        print(f"🔄 [{i}/{len(images)}] {name}...", end=" ", flush=True)

        # Skip if already indexed and valid
        if name in index and index[name].get("character"):
            print("⏭️  Already indexed")
            success += 1
            continue

        t0 = time.time()
        parsed, raw = caption_image(path)
        elapsed = time.time() - t0

        if parsed:
            index[name] = parsed
            # Save incrementally
            with open(INDEX_FILE, 'w') as f:
                json.dump(index, f, indent=2)
            print(f"✅ {elapsed:.1f}s")
            print(f"   CHARACTER: {parsed['character'][:60]}...")
            print(f"   ENVIRONMENT: {parsed['environment'][:60]}...")
            print(f"   COLOR: {parsed['color'][:60]}...")
            success += 1
        else:
            print(f"❌ Failed ({elapsed:.1f}s)")
            print(f"   Raw: {raw[:100]}")
            failed.append(name)

        print()

    print(f"\n{'='*50}")
    print(f"Done: {success}/{len(images)} images indexed")
    if failed:
        print(f"Failed: {len(failed)} — {failed}")
    print(f"Index saved to: {INDEX_FILE}")

if __name__ == "__main__":
    main()
