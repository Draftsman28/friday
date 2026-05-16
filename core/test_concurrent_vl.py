#!/usr/bin/env python3
"""
Concurrent VL Test - Friday Project
Tests if 2 parallel API calls to LM Studio actually speed up on Arc A750.
"""

import asyncio
import aiohttp
import base64
import json
import time
import random
from pathlib import Path

# Config
API_URL = "http://10.146.227.181:1234/v1/chat/completions"
API_KEY = "lm-studio"
IMAGE_DIR = Path.home() / "friday" / "refs"

async def caption_image(session, image_path, call_id):
    """Send one image to Qwen2 VL 2B and time it."""
    start = time.time()

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    ext = image_path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"

    payload = {
        "model": "Qwen2-VL-2B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
                    {"type": "text", "text": "Describe this image in 2 sentences. Be concise."}
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }

    try:
        async with session.post(API_URL, json=payload, headers={"Authorization": f"Bearer {API_KEY}"}) as resp:
            data = await resp.json()
            elapsed = time.time() - start
            caption = data["choices"][0]["message"]["content"]
            return {
                "call_id": call_id,
                "image": image_path.name,
                "elapsed": round(elapsed, 2),
                "caption": caption[:80] + "..." if len(caption) > 80 else caption
            }
    except Exception as e:
        elapsed = time.time() - start
        return {"call_id": call_id, "image": image_path.name, "elapsed": round(elapsed, 2), "error": str(e)}

async def test_concurrent():
    """Fire 2 calls at the same time."""
    images = sorted(IMAGE_DIR.glob("*"))
    if len(images) < 2:
        print(f"Need 2+ images in {IMAGE_DIR}")
        return

    test_images = random.sample(images, 2)
    print(f"\n🖼️  Test images: {[p.name for p in test_images]}")
    print("=" * 50)

    # --- SEQUENTIAL TEST ---
    print("\n[SEQUENTIAL] Processing one at a time...")
    async with aiohttp.ClientSession() as session:
        t0 = time.time()
        r1 = await caption_image(session, test_images[0], "seq-1")
        r2 = await caption_image(session, test_images[1], "seq-2")
        seq_total = time.time() - t0

    print(f"  Call 1: {r1['elapsed']}s")
    print(f"  Call 2: {r2['elapsed']}s")
    print(f"  TOTAL sequential: {round(seq_total, 2)}s")

    # --- CONCURRENT TEST ---
    print("\n[CONCURRENT] Processing both simultaneously...")
    async with aiohttp.ClientSession() as session:
        t0 = time.time()
        r3, r4 = await asyncio.gather(
            caption_image(session, test_images[0], "con-1"),
            caption_image(session, test_images[1], "con-2")
        )
        con_total = time.time() - t0

    print(f"  Call 1: {r3['elapsed']}s")
    print(f"  Call 2: {r4['elapsed']}s")
    print(f"  TOTAL concurrent: {round(con_total, 2)}s")

    # --- RESULTS ---
    print("\n" + "=" * 50)
    speedup = round(seq_total / con_total, 2) if con_total > 0 else 0
    print(f"📊 SPEEDUP: {speedup}×")
    if speedup >= 1.8:
        print("✅ EXCELLENT — True parallelism working. Use concurrent indexer.")
    elif speedup >= 1.3:
        print("🟡 OKAY — Moderate overlap. Concurrent still worth it.")
    else:
        print("🔴 POOR — GPU is serializing. Stick to single-thread.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_concurrent())
