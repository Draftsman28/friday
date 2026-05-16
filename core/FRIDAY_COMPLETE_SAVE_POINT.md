# Friday Project — Complete Save Point

**Date:** 2026-05-16 | **Session:** 4 | **Status:** FUNCTIONAL_BUT_ROUGH

## What Is Friday

Terminal-native voice-to-image reference retrieval tool for visual artists on Fedora 44.

**Origin:** Visual artist (draftsman) needs to find reference images by speaking or typing natural descriptions.

**Workflow:** Voice/text query → search local image library → open results in image viewer on drawing tablet

**Constraints:** Local-first only, no cloud APIs, no heavy GPU compute, terminal-first approach

## Hardware

- CPU: AMD Ryzen 5 5600X
- GPU: Intel Arc A750 (8GB VRAM)
- RAM: 16GB DDR4
- OS: Fedora 44
- Displays: DP-3 (3328x1872 — XP-Pen drawing tablet), DP-1 (2560x1600 — Acer monitor)
- Mic: None (Bluetooth dead)

## What Works Right Now

1. **Type query → see images on XP-Pen**
   ```bash
   python ~/friday/core/friday_text.py
   # Type: combat, samurai, sword, training
   ```

2. **Multiple results = multiple tiled windows**

3. **Auto-detects LM Studio IP after reboot**

4. **Close all windows:** `xdotool search --name '^friday-ref-' | xargs xdotool windowclose`

## What Is Broken

1. **Voice input** — no mic, Bluetooth dead
2. **Search misses partial matches** — 'warrior' not found (exact word only)
3. **3 images have broken captions** — JSON parse failures during re-index
4. **Model hallucinates** — Qwen2 VL 2B outputs dicts instead of strings, copies examples

## Next Session (Critical)

1. Fix search to substring matching
2. Manually fix 3 broken image captions
3. Test random words: tree, blue, angry, city, alone, fire, female, portrait

## File Inventory

**Active:**
- `friday_text.py` — Main pipeline
- `search_friday.py` — Keyword search
- `reindex_all.py` — Full re-indexer

**Inactive (built but unused/broken):**
- `listen.py` — Vosk voice (no mic)
- `index_multi_lens_*.py` — Various indexer attempts (superseded)
- `search_multi_lens_*.py` — Various search attempts (superseded)

## MVP Deadline

**June 1, 2026** — 15 days remaining

**Confidence:** Will hit MVP if voice is deprioritized and search fixes are made in next 1-2 sessions.
