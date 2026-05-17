#!/usr/bin/env python3
"""
Friday Combat Domain Re-Indexer
Re-indexes only combat images with fight-choreographer prompt.
"""

import base64
import json
import time
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

API_URL = "http://10.146.227.181:1234/v1/chat/completions"
API_KEY = "lm-studio"
MODEL_NAME = "bartowski/qwen2-vl-2b-instruct"
IMAGE_DIR = Path.home() / "friday" / "refs"
OUTPUT_FILE = Path.home() / "friday" / "captions_multi_lens.json"
MAX_IMAGE_DIM = 1024

COMBAT_PROMPT = """You are a fight choreographer and action cinematographer analyzing a combat/training image for a production team.

Output EXACTLY ONE JSON object:
{"lenses": ["lens1", "lens2", "lens3"], "captions": {"lens1": "...", "lens2": "...", "lens3": "..."}}

Pick exactly 3 from: character, environment, color, motion, composition, narrative.

CRITICAL RULES:
1. Use vivid, specific language. Name exact colors, textures, weapon types, stances.
2. For character: describe body mechanics, facial intensity, costume wear, physical condition.
3. For motion: describe kinetic energy, momentum direction, implied next move, weight distribution.
4. For narrative: describe the dramatic subtext — training, duel, ambush, last stand, betrayal.
5. NEVER use generic phrases like "the image features", "the scene shows", "there is a".
6. NEVER output markdown fences or JSON arrays."""

COMBAT_FILES = [
    "savethr.com_1777320323223.jpg",
    "savethr.com_1777320351002.jpg",
    "savethr.com_1777320353495.jpg",
]

def resize_image(src_path, max_dim=MAX_IMAGE_DIM):
    if shutil.which("identify"):
        try:
            result = subprocess.run(["identify", "-format", "%w %h", str(src_path)], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                w, h = map(int, result.stdout.strip().split())
                if w <= max_dim and h <= max_dim:
                    return src_path
        except Exception:
            pass
    if shutil.which("convert"):
        tmp = Path("/tmp") / f"friday_{src_path.name}"
        try:
            subprocess.run(["convert", str(src_path), "-resize", f"{max_dim}x{max_dim}>", "-strip", str(tmp)], check=True, capture_output=True, timeout=30)
            if tmp.exists():
                return tmp
        except Exception:
            pass
    return src_path

def encode_image(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = path.suffix.lower().replace(".", "")
    if ext == "jpg": ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"

def caption_image(image_path):
    start = time.time()
    processed = resize_image(image_path)
    img_b64 = encode_image(processed)
    if processed != image_path and "/tmp/" in str(processed):
        try: processed.unlink()
        except: pass

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": img_b64}}, {"type": "text", "text": COMBAT_PROMPT}]}],
        "temperature": 0.15,
        "max_tokens": 400
    }
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start
            raw = data["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.split("```json")[-1].split("```")[0].strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list): parsed = parsed[0] if parsed else {}
            if not isinstance(parsed, dict):
                return {"file": image_path.name, "error": f"bad type {type(parsed)}", "elapsed": round(elapsed, 2)}
            return {"file": image_path.name, "lenses": parsed.get("lenses", []), "captions": parsed.get("captions", {}),
                    "elapsed": round(elapsed, 2), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"file": image_path.name, "error": str(e), "elapsed": round(time.time() - start, 2)}

def main():
    index = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            index = json.load(f)

    images = [IMAGE_DIR / f for f in COMBAT_FILES if (IMAGE_DIR / f).exists()]
    print(f"Re-indexing {len(images)} combat images...")

    for img in images:
        print(f"\n🔄 {img.name}")
        res = caption_image(img)
        if "error" in res:
            print(f"   ❌ {res['error']} ({res['elapsed']}s)")
        else:
            index[res["file"]] = res
            print(f"   ✅ {res['elapsed']}s | {', '.join(res['lenses'])}")
            for ln, cap in res["captions"].items():
                short = cap[:90] if len(cap) > 90 else cap
                print(f"      [{ln}] {short}...")

        with open(OUTPUT_FILE, "w") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"   💾 Saved")

    print(f"\n🎉 Done. {len(index)} total images in index.")

if __name__ == "__main__":
    import urllib.request
    import urllib.error
    main()
