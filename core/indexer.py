#!/usr/bin/env python3
"""
Friday Re-Indexer — Generic example so model can't copy it.
"""

import base64
import json
import time
import subprocess
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
import config

def get_endpoint():
    if config.CONFIG_FILE.exists():
        return config.CONFIG_FILE.read_text().strip()
    return config.DEFAULT_ENDPOINT

# Generic example with placeholders — model CANNOT copy this
PROMPT = """Analyze this image. Return ONLY JSON:

{"lenses":["character","environment","color"],"captions":{"character":"[describe the person/figure]","environment":"[describe the setting]","color":"[describe the palette]"}}

Rules:
- Pick 3 lenses from: character, environment, color, motion, composition, narrative
- Each caption: 1 sentence, vivid, specific. Name exact colors, textures, moods.
- Do NOT copy the example text above. Write about THIS image.
- No markdown. Only JSON."""

def resize_image(src_path, max_dim=config.MAX_IMAGE_DIM):
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

    API_URL = get_endpoint()
    payload = {
        "model": config.MODEL_NAME,
        "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": img_b64}}, {"type": "text", "text": PROMPT}]}],
        "temperature": 0.2,
        "max_tokens": 300
    }
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.API_KEY}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start
            raw = data["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list): parsed = parsed[0] if parsed else {}
            if not isinstance(parsed, dict):
                return {"file": image_path.name, "error": f"bad type {type(parsed)}", "elapsed": round(elapsed, 2)}
            return {"file": image_path.name, "lenses": parsed.get("lenses", []), "captions": parsed.get("captions", {}),
                    "elapsed": round(elapsed, 2), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"file": image_path.name, "error": str(e), "elapsed": round(time.time() - start, 2)}

def main():
    if not config.IMAGE_DIR.exists():
        print(f"Error: Image directory not found at {config.IMAGE_DIR}")
        return

    images = sorted([p for p in config.IMAGE_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}])
    print(f"Re-indexing {len(images)} images...")
    index = {}

    for i, img in enumerate(images, 1):
        print(f"\n🔄 [{i}/{len(images)}] {img.name}")
        res = caption_image(img)
        if "error" in res:
            print(f"   ❌ {res['error']} ({res['elapsed']}s)")
        else:
            index[res["file"]] = res
            print(f"   ✅ {res['elapsed']}s | {', '.join(res['lenses'])}")
            for ln, cap in res["captions"].items():
                short = cap[:90] if len(cap) > 90 else cap
                print(f"      [{ln}] {short}...")

        with open(config.INDEX_FILE, "w") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"   💾 Saved ({len(index)}/{len(images)})")

    print(f"\n🎉 Done. {len(index)} images indexed.")

if __name__ == "__main__":
    main()
