#!/usr/bin/env python3
"""
Friday Multi-Lens Concurrent Indexer
Processes 2 images at a time via LM Studio Parallel 2.
Single API call per image → Qwen2 VL 2B picks 3 best lenses → JSON output.
"""

import asyncio
import aiohttp
import base64
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# ─── CONFIG ───
API_URL = "http://10.146.227.181:1234/v1/chat/completions"
API_KEY = "lm-studio"
MODEL_NAME = "Qwen2-VL-2B-Instruct"
IMAGE_DIR = Path.home() / "friday" / "refs"
OUTPUT_FILE = Path.home() / "friday" / "captions_multi_lens.json"
BATCH_SIZE = 2  # Match LM Studio Parallel slots

LENSES = ["character", "environment", "color", "motion", "composition", "narrative"]

PROMPT = """You are an expert visual art analyst. Look at this image and write captions from the 3 most relevant analytical lenses.

Available lenses: character, environment, color, motion, composition, narrative.

Rules:
- Pick exactly 3 lenses that best describe this image.
- Write 1-2 rich sentences per lens.
- Be specific: name colors, moods, spatial relationships, implied story.
- Output ONLY valid JSON. No markdown, no explanations.

Format:
{
  "lenses": ["lens1", "lens2", "lens3"],
  "captions": {
    "lens1": "...",
    "lens2": "...",
    "lens3": "..."
  }
}"""

# ─── HELPERS ───

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

async def process_one(session, image_path, semaphore):
    """Caption a single image through the semaphore."""
    async with semaphore:
        img_b64 = encode_image(image_path)
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
            "temperature": 0.2,
            "max_tokens": 400
        }

        start = time.time()
        try:
            async with session.post(
                API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                data = await resp.json()
                elapsed = time.time() - start

                if "choices" not in data:
                    return {
                        "file": image_path.name,
                        "error": f"No choices in response: {data.get('error', 'unknown')}",
                        "elapsed": round(elapsed, 2)
                    }

                raw = data["choices"][0]["message"]["content"]
                # Strip markdown fences if present
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("```json")[-1].split("```")[0].strip()

                parsed = json.loads(raw)
                return {
                    "file": image_path.name,
                    "lenses": parsed.get("lenses", []),
                    "captions": parsed.get("captions", {}),
                    "elapsed": round(elapsed, 2),
                    "timestamp": datetime.now().isoformat()
                }
        except asyncio.TimeoutError:
            return {"file": image_path.name, "error": "Timeout (>120s)", "elapsed": 120}
        except Exception as e:
            return {"file": image_path.name, "error": str(e), "elapsed": round(time.time() - start, 2)}

async def main():
    images = sorted([p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp"}])
    if not images:
        print(f"No images found in {IMAGE_DIR}")
        sys.exit(1)

    index = load_existing()
    already_done = set(index.keys())
    pending = [p for p in images if p.name not in already_done]

    print(f"\n📁 Total images: {len(images)}")
    print(f"✅ Already indexed: {len(already_done)}")
    print(f"⏳ Pending: {len(pending)}")
    print(f"⚡ Batch size: {BATCH_SIZE} (LM Studio Parallel slots)")
    print(f"🎯 Model: {MODEL_NAME}")
    print("=" * 50)

    if not pending:
        print("Nothing to do. All images already indexed.")
        return

    semaphore = asyncio.Semaphore(BATCH_SIZE)
    session_timeout = aiohttp.ClientTimeout(total=180)

    async with aiohttp.ClientSession(timeout=session_timeout) as session:
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"\n🔄 Batch {batch_num}/{total_batches}: {[p.name for p in batch]}")
            batch_start = time.time()

            results = await asyncio.gather(*[
                process_one(session, img, semaphore) for img in batch
            ])

            batch_elapsed = time.time() - batch_start

            for res in results:
                if "error" in res:
                    print(f"   ❌ {res['file']}: ERROR — {res['error']} ({res['elapsed']}s)")
                else:
                    index[res["file"]] = res
                    print(f"   ✅ {res['file']}: {res['elapsed']}s | Lenses: {', '.join(res['lenses'])}")

            save_index(index)
            print(f"   💾 Saved. Batch wall time: {round(batch_elapsed, 2)}s")

    print("\n" + "=" * 50)
    print(f"🎉 DONE. Indexed {len(index)} total images.")
    print(f"📄 Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
