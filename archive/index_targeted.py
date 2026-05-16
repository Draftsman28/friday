#!/usr/bin/env python3
"""
Friday Targeted Domain Indexer
Only re-indexes images matching chosen domains with domain-specific prompts.
Much higher quality than generic prompts.
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

# Domain-specific prompts — much richer than generic
DOMAINS = {
    "combat": """You are a fight choreographer and action cinematographer analyzing a combat/training image.
Output EXACTLY ONE JSON object:
{"lenses": ["lens1", "lens2", "lens3"], "captions": {"lens1": "...", "lens2": "...", "lens3": "..."}}
Pick from: character, environment, color, motion, composition, narrative.
Focus on: weapon handling, body mechanics, spatial tension between fighters, dramatic lighting on conflict, implied backstory of the duel.
Use vivid, specific language. Name exact colors, textures, stances.""",

    "portrait": """You are a portrait photographer and character designer analyzing a face/figure image.
Output EXACTLY ONE JSON object:
{"lenses": ["lens1", "lens2", "lens3"], "captions": {"lens1": "...", "lens2": "...", "lens3": "..."}}
Pick from: character, environment, color, motion, composition, narrative.
Focus on: facial expression micro-details, costume texture and wear, lighting direction on skin, posture psychology, implied emotional state.
Use vivid, specific language. Name exact colors, materials, emotions.""",

    "atmosphere": """You are a production designer and lighting director analyzing a mood/environment image.
Output EXACTLY ONE JSON object:
{"lenses": ["lens1", "lens2", "lens3"], "captions": {"lens1": "...", "lens2": "...", "lens3": "..."}}
Pick from: character, environment, color, motion, composition, narrative.
Focus on: light source quality and direction, weather/atmosphere, color temperature shifts, spatial depth layers, time-of-day mood.
Use vivid, specific language. Name exact colors, lighting ratios, atmospheric effects.""",

    "anime": """You are a manga art director and anime key animator analyzing a stylized image.
Output EXACTLY ONE JSON object:
{"lenses": ["lens1", "lens2", "lens3"], "captions": {"lens1": "...", "lens2": "...", "lens3": "..."}}
Pick from: character, environment, color, motion, composition, narrative.
Focus on: line weight and brushwork, graphic composition, color palette choices, implied motion between panels, psychological subtext.
Use vivid, specific language. Name exact colors, stylistic references, emotional beats."""
}

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

def caption_image(image_path, prompt):
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
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        "temperature": 0.15,
        "max_tokens": 400
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, choices=list(DOMAINS.keys()),
                        help="Domain to index: combat, portrait, atmosphere, anime")
    parser.add_argument("--files", nargs="+", help="Specific filenames to index (optional)")
    args = parser.parse_args()

    prompt = DOMAINS[args.domain]

    images = sorted([p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}])
    if not images:
        print(f"No images found in {IMAGE_DIR}")
        sys.exit(1)

    # Filter to specific files if provided
    if args.files:
        target_images = [p for p in images if p.name in args.files]
        if not target_images:
            print(f"None of the specified files found in {IMAGE_DIR}")
            sys.exit(1)
    else:
        target_images = images

    index = load_existing()
    already_done = set(index.keys())
    pending = [p for p in target_images if p.name not in already_done]

    print(f"\n🎯 Domain: {args.domain}")
    print(f"📁 Target images: {len(target_images)}")
    print(f"✅ Already indexed: {len([p for p in target_images if p.name in already_done])}")
    print(f"⏳ Pending: {len(pending)}")
    print("=" * 50)

    if not pending:
        print("Nothing to do.")
        return

    for i, img in enumerate(pending, 1):
        print(f"\n🔄 [{i}/{len(pending)}] {img.name}")
        res = caption_image(img, prompt)

        if "error" in res:
            print(f"   ❌ ERROR: {res['error']} ({res['elapsed']}s)")
            if "crashed" in res['error'].lower() or "HTTP 500" in res['error']:
                print("   ⏸️  Waiting 5s...")
                time.sleep(5)
        else:
            index[res["file"]] = res
            print(f"   ✅ {res['elapsed']}s | Lenses: {', '.join(res['lenses'])}")
            for ln, cap in res['captions'].items():
                print(f"      [{ln}] {cap[:100]}...")

        save_index(index)
        print(f"   💾 Saved ({len(index)} total in index)")

    print("\n" + "=" * 50)
    success_count = sum(1 for v in index.values() if "error" not in v)
    print(f"🎉 DONE. {success_count} images in index total.")

if __name__ == "__main__":
    import urllib.request
    import urllib.error
    main()
