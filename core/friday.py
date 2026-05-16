#!/usr/bin/env python3
"""
Friday — Text Input, auto-detects LM Studio endpoint.
Scans common local IP ranges, falls back to manual input.
"""

import sys
import subprocess
import shutil
import time
import urllib.request
from pathlib import Path
from core import config

def find_lm_studio():
    """Auto-detect LM Studio server on local network."""
    import socket

    # Common ports and IP patterns
    ports = [1234, 8080, 5000, 8000]

    # Get local IP prefix
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        prefix = ".".join(local_ip.split(".")[:3])
    except Exception:
        prefix = "10.146.227"

    print("   🔍 Scanning for LM Studio...")

    # Check saved endpoint first
    if config.CONFIG_FILE.exists():
        saved = config.CONFIG_FILE.read_text().strip()
        if saved:
            try:
                req = urllib.request.Request(saved.replace("/v1/chat/completions", "/v1/models"),
                    headers={"Content-Type": "application/json"}, method="GET")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        print(f"   ✅ Using saved endpoint: {saved}")
                        return saved
            except Exception:
                pass

    # Scan local subnet
    for port in ports:
        for last_octet in range(1, 255):
            url = f"http://{prefix}.{last_octet}:{port}/v1/models"
            try:
                req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="GET")
                with urllib.request.urlopen(req, timeout=0.5) as resp:
                    if resp.status == 200:
                        endpoint = f"http://{prefix}.{last_octet}:{port}/v1/chat/completions"
                        config.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                        config.CONFIG_FILE.write_text(endpoint)
                        print(f"   ✅ Found LM Studio: {endpoint}")
                        return endpoint
            except Exception:
                continue

    # Fallback: ask user
    print("   ❌ Could not auto-detect LM Studio.")
    manual = input("   Enter LM Studio URL (e.g., http://10.146.227.7:1234): ").strip()
    if not manual.startswith("http"):
        manual = "http://" + manual
    if not manual.endswith("/v1/chat/completions"):
        manual = manual.rstrip("/") + "/v1/chat/completions"
    config.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.CONFIG_FILE.write_text(manual)
    return manual

def open_image_single(filename, idx, total):
    path = str(config.IMAGE_DIR / filename)
    title = f"{config.WINDOW_TITLE_BASE}-{idx}"
    win_w = 3328 // max(total, 1)
    win_x = config.XP_X + (idx * win_w)

    if shutil.which("feh"):
        cmd = ["feh", "--title", title, "--geometry", f"{win_w}x800+{win_x}+{config.XP_Y}", "--scale-down", path]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   🖼️  [{idx+1}] {filename} | title: '{title}'")
            if shutil.which("xdotool"):
                time.sleep(0.3)
                subprocess.Popen(
                    f"winid=$(xdotool search --name '^{title}$' | head -1); [ -n \"$winid\" ] && xdotool windowmove $winid {win_x} {config.XP_Y}",
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            return proc
        except Exception as e:
            print(f"   ⚠️  feh failed: {e}")
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None

def search_query(query):
    # Using sys.executable to run search.py as a script to maintain original behavior
    # while allowing it to be part of the module.
    result = subprocess.run([sys.executable, "-m", "core.search", query], capture_output=True, text=True, timeout=30)
    return result.stdout, result.stderr

def main():
    print("=" * 50)
    print("🗓️  FRIDAY — Type query → images on XP-Pen")
    print("=" * 50)

    # Auto-detect or configure LM Studio
    endpoint = find_lm_studio()
    print(f"   📡 API: {endpoint}")

    while True:
        try:
            query = input("\n🔍 Search: ").strip()
            if not query:
                continue

            print("   Searching...")
            stdout, stderr = search_query(query)
            if stderr:
                print(stderr, file=sys.stderr)

            lines = stdout.strip().split("\n")
            filenames = []
            for line in lines:
                if line.strip() and line[0].isdigit() and "." in line:
                    parts = line.split(" ")
                    if len(parts) > 1:
                        fname = parts[1].strip()
                        if fname:
                            filenames.append(fname)

            if not filenames:
                print("   No results.")
                continue

            for line in lines:
                print(line)

            print(f"\n   Opening {len(filenames)} window(s)...")
            for i, fname in enumerate(filenames[:5]):
                open_image_single(fname, i, len(filenames[:5]))

            print(f"\n   💡 Close all: xdotool search --name '^friday-ref-' | xargs xdotool windowclose")

        except KeyboardInterrupt:
            print("\n👋 Goodbye.")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    main()
