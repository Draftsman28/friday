#!/usr/bin/env python3
"""
Friday Multi-Lens Indexer v4
- Stronger prompt forcing vivid, specific language
- Single-threaded, auto-resize, robust parsing
- For bartowski/qwen2-vl-2b-instruct
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

PROMPT = """You are a senior cinematographer and visual art director analyzing a reference image for a production team.

Analyze the image and output EXACTLY ONE JSON object:

{
  "lenses": ["lens1", "lens2", "lens3"],
  "captions": {
    "lens1": "...",
    "lens2": "...",
    "lens3": "..."
  }
}

CRITICAL RULES:
1. Pick exactly 3 lenses from: character, environment, color, motion, composition, narrative
2. Write like you are briefing a director of photography. Be vivid, specific, and evocative.
3. Name exact colors (crimson, ochre, slate blue), textures, lighting qualities, spatial depth.
4. For narrative: describe the implied story, emotional tension, or dramatic subtext.
5. For motion: describe implied movement, energy flow, or kinetic tension even in still frames.
6. NEVER use generic phrases like "the image features", "the scene shows", "there is a".
7. NEVER output markdown fences. NEVER output a JSON array []. NEVER output multiple objects.
8. Each caption must be 1-2 dense, art-direction-quality sentences."""

def resize_image(src_path, max_dim=MAX_IMAGE_DIM):
    dim_cmd = None
    if shutil.which("identify"):
        dim_cmd = ["identify", "-format", "%w %h", str(src_path)]
    elif shutil.which("ffprobe"):
        dim_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "csv=p=0", str(src_path)]

    width, height = 0, 0
    if dim_cmd:
        try:
            result = subprocess.run(dim_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                out = result.stdout.strip()
                if shutil.which("identify"):
                    parts = out.split()
                    width, height = int(parts[0]), int(parts[1])
                elif shutil.which("ffprobe"):
                    parts = out.split(",")
                    width, height = int(parts[0]), int(parts[1])
        except Exception:
            pass

    if width <= max_dim and height <= max_dim:
        return src_path

    if shutil.which("convert"):
        tmp_path = Path("/tmp") / f"friday_resize_{src_path.name}"
        cmd = ["convert", str(src_path), "-resize", f"{max_dim}x{max_dim}>", "-strip", str(tmp_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            if tmp_path.exists():
                print(f"   📐 Resized {src_path.name} ({width}x{height} → max {max_dim}px)")
                return tmp_path
        except Exception as e:
            print(f"   ⚠️  Resize failed: {e}")

    if shutil.which("ffmpeg"):
        tmp_path = Path("/tmp") / f"friday_resize_{src_path.name}"
        cmd = ["ffmpeg", "-y", "-i", str(src_path), "-vf", f"scale='min({max_dim},iw)':-1",
               "-q:v", "2", str(tmp_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            if tmp_path.exists():
                print(f"   📐 Resized {src_path.name} ({width}x{height} → max {max_dim}px)")
                return tmp_path
        except Exception as e:
            print(f"   ⚠️  Resize failed: {e}")

    return src_path

def encode_image(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"

def load_existing():
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    return {}

def save_index(index):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def caption_image(image_path):
    start = time.time()
    processed_path = resize_image(image_path)
    img_b64 = encode_image(processed_path)

    if processed_path != image_path and "/tmp/" in str(processed_path):
        try:
            processed_path.unlink()
        except Exception:
            pass

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_b64}},
                    {"type": "text", "text": PROMPT}
                ]
            }
        ],
        "temperature": 0.15,
        "max_tokens": 400
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start

            if "choices" not in data or not data["choices"]:
                return {"file": image_path.name, "error": "Empty choices", "elapsed": round(elapsed, 2)}

            raw = data["choices"][0]["message"]["content"]
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```json")[-1].split("```")[0].strip()
            elif raw.startswith("```"):
                raw = raw[3:].strip()
                if raw.endswith("```"):
                    raw = raw[:-3].strip()

            parsed = json.loads(raw)

            if isinstance(parsed, list):
                if len(parsed) == 0:
                    return {"file": image_path.name, "error": "Empty list response", "elapsed": round(elapsed, 2)}
                parsed = parsed[0]

            if not isinstance(parsed, dict):
                return {"file": image_path.name, "error": f"Response is {type(parsed).__name__}", "elapsed": round(elapsed, 2)}

            lenses = parsed.get("lenses", [])
            captions = parsed.get("captions", {})

            if len(lenses) == 0:
                return {"file": image_path.name, "error": "No lenses found", "elapsed": round(elapsed, 2)}

            return {
                "file": image_path.name,
                "lenses": lenses,
                "captions": captions,
                "elapsed": round(elapsed, 2),
                "timestamp": datetime.now().isoformat()
            }

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:200]
        return {"file": image_path.name, "error": f"HTTP {e.code}: {body}", "elapsed": round(time.time() - start, 2)}
    except json.JSONDecodeError as e:
        return {"file": image_path.name, "error": f"JSON parse failed: {e}", "elapsed": round(time.time() - start, 2)}
    except Exception as e:
        return {"file": image_path.name, "error": str(e), "elapsed": round(time.time() - start, 2)}

def main():
    images = sorted([p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}])
    if not images:
        print(f"No images found in {IMAGE_DIR}")
        sys.exit(1)

    index = load_existing()
    already_done = set(index.keys())
    pending = [p for p in images if p.name not in already_done]

    print(f"\n📁 Total images: {len(images)}")
    print(f"✅ Already indexed: {len(already_done)}")
    print(f"⏳ Pending: {len(pending)}")
    print(f"📐 Max dimension: {MAX_IMAGE_DIM}px")
    print(f"🎯 Model: {MODEL_NAME}")
    print("=" * 50)

    if not pending:
        print("Nothing to do. All images already indexed.")
        return

    for i, img in enumerate(pending, 1):
        print(f"\n🔄 [{i}/{len(pending)}] {img.name}")
        res = caption_image(img)

        if "error" in res:
            print(f"   ❌ ERROR: {res['error']} ({res['elapsed']}s)")
            if "crashed" in res['error'].lower() or "HTTP 500" in res['error']:
                print("   ⏸️  Waiting 5s for LM Studio recovery...")
                time.sleep(5)
        else:
            index[res["file"]] = res
            print(f"   ✅ {res['elapsed']}s | Lenses: {', '.join(res['lenses'])}")
            for ln, cap in res['captions'].items():
                print(f"      [{ln}] {cap[:100]}...")

        save_index(index)
        print(f"   💾 Saved ({len(index)}/{len(images)} total)")

    print("\n" + "=" * 50)
    success_count = sum(1 for v in index.values() if "error" not in v)
    print(f"🎉 DONE. {success_count}/{len(images)} images successfully indexed.")
    print(f"📄 Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    import urllib.request
    import urllib.error
    main()
