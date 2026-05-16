# FRIDAY PROJECT — COMPLETE DEVELOPMENT SUMMARY
## Session 4 | 2026-05-16 | Status: FUNCTIONAL_BUT_ROUGH

---

## 1. WHAT IS FRIDAY

**Friday** is a terminal-native, voice-to-image reference retrieval tool for a visual artist (draftsman) working on Fedora 44.

**Core Problem:** The user collects thousands of reference images but loses time and focus searching through folders while drawing. Friday solves this by letting the artist speak or type a description and instantly seeing matching reference images on their XP-Pen drawing tablet.

**One-Sentence Mission:** *"You speak. It finds your reference images. You see them. You keep drawing."*

---

## 2. HARDWARE SPECIFICATIONS

| Component | Specification | Role in Friday |
|-----------|--------------|----------------|
| **CPU** | AMD Ryzen 5 5600X | Runs all Python backend, search, voice processing |
| **GPU** | Intel Arc A750 (8GB VRAM) | Runs Qwen2 VL 2B in LM Studio for image captioning |
| **RAM** | 16GB DDR4 | Shared between Krita/Blender and Friday processes |
| **OS** | Fedora 44 | Terminal-first, KDE Plasma environment |
| **Primary Display** | DP-3 — XP-Pen 3328×1872 | Where reference images open (drawing tablet) |
| **Secondary Display** | DP-1 — Acer 2560×1600 | Where terminal lives |
| **Microphone** | NONE (Bluetooth dead, no USB headset) | Voice pipeline blocked until hardware fixed |
| **Internet** | Moto Edge 50 USB tethering | Limited bandwidth — local-first mandatory |

**Critical Constraint:** 16GB total RAM means Krita/Blender + LM Studio + Friday must coexist. No room for heavy GPU compute or local LLMs.

---

## 3. DEVELOPMENT TIMELINE (4 Sessions)

### Session 1 (~May 10)
- **What happened:** Initial vision document shared. Single-caption expert indexing with Qwen VL 7B tested. CLIP-based search proposed and **rejected by user** — wants LLM-only approach.
- **Decisions locked:** Local-first only, no cloud APIs, Python backend, terminal-first approach.
- **Stack defined:** Vosk for voice, Qwen VL for vision, feh/imv for display.

### Session 2 (~May 12)
- **What happened:** WebP → JPG conversion completed. Basic keyword search (`search_friday.py`) built and working. File inventory organized into categories (combat/action, portrait, landscape, anime, scifi).
- **Milestone:** First working search — "combat" returns samurai images.
- **Problem discovered:** Exact-word matching only. "warrior" misses "warriors." "sword" misses "swords."

### Session 3 (~May 14)
- **What happened:** Multi-lens architecture designed (6 perspectives: character, environment, color, motion, composition, narrative). Multiple indexer attempts:
  - `index_multi_lens_fast.py` — concurrent indexing, **crashed on VRAM** (Arc A750 couldn't handle it)
  - `index_multi_lens_v2.py` — multi-call per image, **too slow** (60-100s/image, LM Studio log spam)
  - `index_multi_lens_fast.py` (v2) — single API call per image, **approved** (~15-25s/image)
- **Key insight:** User explicitly rejected CLIP embeddings, wants LLM-generated captions only.
- **Pivot:** Abandoned multi-lens concurrent approach. Settled on single-call multi-lens with Qwen VL picking 3 best lenses per image.

### Session 4 (May 16) — CURRENT
- **What happened:**
  - Text input pipeline fully working: `friday_text.py`
  - Auto-detects LM Studio IP after reboot (saves to `~/friday/api_endpoint.txt`)
  - Multiple results open as tiled windows on XP-Pen
  - 3 re-index attempts made, JSON reliability issues with Qwen2 VL 2B
  - `reindex_all.py` created with minimal prompt to prevent example copying
  - Concurrency test with Parallel 2 slots — works but marginal speedup (~1.3x)
- **Current blockers:**
  1. Search uses exact-word regex (`\bquery\b`) — misses partial matches
  2. 3 images have broken captions from JSON parse failures
  3. Voice input not implemented (no microphone hardware)
  4. Model hallucinates — outputs dicts instead of strings, copies examples from prompt

---

## 4. WHAT WORKS RIGHT NOW

### ✅ Working Features

| Feature | Script | Status | Details |
|---------|--------|--------|---------|
| **Text query → images** | `friday_text.py` | ✅ WORKING | Type query, search, open on XP-Pen |
| **Auto-detect LM Studio** | `friday_text.py` | ✅ WORKING | Detects IP, saves to `api_endpoint.txt` |
| **Multiple results** | `friday_text.py` | ✅ WORKING | Tiled windows, 3328px / N images |
| **Image indexing** | `reindex_all.py` | ✅ WORKING | Single-call, auto-resize to 1024px, incremental save |
| **Keyword search** | `search_friday.py` | ✅ WORKING | Instant, local JSON, no API calls |
| **Close all windows** | `xdotool` | ✅ WORKING | `xdotool search --name '^friday-ref-' \| xargs xdotool windowclose` |

### Working Commands
```bash
# Run Friday (text input)
python ~/friday/core/friday_text.py

# Direct search
python ~/friday/core/search_friday.py <query>

# Re-index all images
python ~/friday/core/reindex_all.py

# Close all image windows
xdotool search --name '^friday-ref-' | xargs xdotool windowclose
```

### Tested Working Queries
- "combat" → finds samurai training images
- "samurai" → finds warrior images
- "sword" → finds weapon images
- "training" → finds practice/fight scenes

---

## 5. WHAT IS BROKEN

### 🔴 Critical Issues

| Issue | Impact | Root Cause | Fix Planned |
|-------|--------|------------|-------------|
| **Exact-word search only** | HIGH | Regex uses `\bword\b` | Switch to substring matching |
| **3 broken captions** | MEDIUM | Qwen2 VL 2B outputs malformed JSON | Manual fix or delete, re-index with plain text prompt |
| **Model hallucination** | MEDIUM | 2B model copies examples, outputs dicts | Simplify prompt, remove examples, use plain text output |
| **Voice input missing** | HIGH | No microphone hardware | Deprioritized for MVP; text-only for June 1 |
| **"warrior" not found** | MEDIUM | "warrior" not in captions | Substring fix will resolve |
| **"swords" not found** | MEDIUM | Plural not matched | Substring fix will resolve |
| **Compound queries fail** | MEDIUM | "2 person", "dramatic face" | Substring + ranking score |

### Broken Images (3/20)
1. `pexels-ambient_nature_-atmosphere-1682386-14700048.jpg` — JSON parse fail
2. `682724649_18071771450649885_1390397772722532039_n.jpg` — JSON parse fail
3. `684280661_18071771453649885_9088713570570443621_n.jpg` — JSON parse fail

### Not Working Queries
- "warrior" — not in captions (exact word only)
- "swords" — plural not matched
- "2 person" — compound fails
- "thumbnail" — not in captions
- "mat" — not in captions
- "dramatic face" — compound fails

---

## 6. FILE INVENTORY

### Active Scripts (In Use)

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `friday_text.py` | `~/friday/core/` | Main pipeline: text → search → feh | ✅ WORKING |
| `search_friday.py` | `~/friday/core/` | Keyword search on captions | ✅ WORKING |
| `reindex_all.py` | `~/friday/core/` | Full re-indexer, minimal prompt | ✅ WORKING |

### Inactive Scripts (Built but Unused/Broken)

| File | Status | Why Unused |
|------|--------|------------|
| `listen.py` | ❌ NOT WORKING | No microphone; Vosk model downloaded but never tested |
| `index_multi_lens_fast.py` | ⚠️ SUPERSEDED | Concurrent crashed on VRAM; replaced by `reindex_all.py` |
| `index_multi_lens_robust.py` | ⚠️ SUPERSEDED | Replaced by `reindex_all.py` |
| `index_multi_lens_concurrent.py` | ❌ BROKEN | VRAM crash on Arc A750 |
| `index_targeted.py` | ⚠️ UNUSED | Domain-specific indexer, not needed |
| `survey_domains.py` | ⚠️ UNUSED | Debug tool, shows all captions |
| `search_multi_lens.py` | ⚠️ SUPERSEDED | Obsolete keyword search |
| `search_multi_lens_llm.py` | ⚠️ SUPERSEDED | LLM expansion was non-deterministic |
| `search_multi_lens_semantic.py` | ❌ REJECTED | CLIP-based, user explicitly rejected |
| `search_vl_expert.py` | ⚠️ UNUSED | CLIP-based, loads HF Hub |
| `test_concurrent_vl.py` | ⚠️ TEST | Used once for concurrency test |
| `test_concurrent_vl_threaded.py` | ⚠️ TEST | Used once |
| `build_embeddings.py` | ❌ REJECTED | CLIP embeddings, user rejected |

### Data Files

| File | Location | Contents |
|------|----------|----------|
| `captions_multi_lens.json` | `~/friday/` | Current index (20 images, 3 broken) |
| `captions_expert.json` | `~/friday/` | Legacy single-caption index (20 images, unused) |
| `api_endpoint.txt` | `~/friday/` | LM Studio URL cache (auto-detected) |

### Model Files

| File | Location | Size | Status |
|------|----------|------|--------|
| Vosk model | `~/friday/models/vosk-model-small-en-us-0.15/` | ~40MB | Downloaded, UNUSED |
| Qwen2 VL 2B | LM Studio | ~6GB loaded | Active, Parallel 2 slots |

---

## 7. APPROVED ARCHITECTURE STACK

### Locked-In Decisions

| Layer | Technology | Reason |
|-------|-----------|--------|
| **Voice Input** | Vosk (offline) | Local-only, no cloud, ~40MB model |
| **Vision Model** | Qwen2 VL 2B Instruct | Fits in 8GB VRAM, fast enough (~2-4s/image at 1024px) |
| **Backend** | Python 3 | User comfortable, rich ecosystem |
| **Image Viewer** | feh / imv | Lightweight, terminal-launched, no chrome |
| **Display Target** | XP-Pen DP-3 | Primary drawing surface, 3328×1872 |
| **Approach** | Terminal-first, headless | No GUI framework overhead |
| **Concurrency** | Parallel 2 (LM Studio) | Marginal speedup, stable on Arc A750 |

### AI Stack Details

```
Vision Model: bartowski/qwen2-vl-2b-instruct
  Size: 2B parameters
  Backend: LM Studio (local server)
  URL: http://10.146.227.7:1234 (auto-detected)
  Parallel Slots: 2
  Indexing Speed: ~2-4s per image (resized to 1024px)
  JSON Reliability: POOR — hallucinates, outputs dicts, copies examples
  Quality: Acceptable for basic captions, unreliable for structured output

Voice Model: vosk-model-small-en-us-0.15
  Size: ~40MB
  Status: Downloaded but UNUSED — no microphone available
```

---

## 8. REJECTED IDEAS (DO NOT REVISIT BEFORE JUNE 1)

| Idea | Why Rejected | When Rejected |
|------|-------------|---------------|
| **PyQt6 GUI** | Too heavy, fights compositor on Intel Arc | Session 3 |
| **KRunner integration** | KDE-specific, C++ compilation overhead | Session 3 |
| **Clicky cursor pet** | Resource waste, distracting, not needed for MVP | Session 3 |
| **Transparent overlays** | Compositor bugs on Intel Arc, fragile | Session 3 |
| **Persistent mascot/avatar** | Visual noise while drawing | Session 3 |
| **Local LLM (Hermes/Ollama)** | 16GB RAM cannot handle alongside art software | Session 3 |
| **Obsidian integration** | Parsing complexity, not needed for image retrieval | Session 1 |
| **Moodboard auto-grouping** | Algorithms for v2, grid is fine for MVP | Session 1 |
| **CLIP embeddings** | User explicitly rejected — wants LLM-only captions | Session 1 |
| **Concurrent indexing** | VRAM crash on Arc A750 (8GB insufficient) | Session 3 |
| **Multi-call-per-image indexing** | Too slow (60-100s/image), LM Studio log spam | Session 3 |
| **LLM query expansion** | Non-deterministic, added latency without clear benefit | Session 3 |

---

## 9. NEXT SESSION CRITICAL PATH (Session 5)

### Priority 1: FIX SEARCH (Critical)
**Problem:** Exact-word regex (`\bquery\b`) misses valid results.
**Solution:** Switch to substring matching.
**Expected improvement:** "war" finds "warrior", "sword" finds "swords", "train" finds "training".
**Effort:** 30 minutes — change one regex line in `search_friday.py`.

### Priority 2: FIX BROKEN CAPTIONS (Critical)
**Problem:** 3 images have empty/broken captions from JSON parse failures.
**Solution:** 
- Option A: Manually delete broken entries, re-index those 3 images with simplified plain-text prompt (no JSON)
- Option B: Delete the 3 images from index entirely
**Effort:** 15-30 minutes.

### Priority 3: RANDOM WORD TESTING (Validation)
**Test queries:** tree, blue, angry, city, alone, fire, female, portrait
**Purpose:** Validate that substring search works across diverse vocabulary.
**Effort:** 10 minutes.

### Priority 4: VOICE PIPELINE (Important, Blocked)
**Status:** Cannot proceed without microphone hardware.
**Options:**
- Fix Bluetooth
- Buy USB headset
- Deprioritize for MVP (text-only is functional)

---

## 10. MVP ASSESSMENT

| Component | Completion | Grade |
|-----------|-----------|-------|
| **Text Pipeline** | 80% | B+ — works for common queries, misses some |
| **Voice Pipeline** | 0% | F — blocked by hardware |
| **Search Quality** | 60% | C — exact word only, no semantics |
| **Index Quality** | 70% | C+ — 12 good, 5 mediocre, 3 broken |
| **Image Viewer** | 90% | A- — opens on correct monitor, tiled windows work |
| **Overall** | **~65%** | **C+ (Functional but rough)** |

### Confidence: HIGH
**Will hit MVP if:**
1. Voice is deprioritized (text-only is acceptable)
2. Search substring fix is made in next 1-2 sessions
3. 3 broken captions are repaired

**Risk:** Voice hardware not fixable by June 1 → MVP ships text-only.

---

## 11. IMAGE LIBRARY BREAKDOWN

**Total Images:** 20
**Location:** `~/friday/refs/`
**Formats:** jpg, png, jpeg (all webp converted)

| Category | Count | Example Filenames |
|----------|-------|-------------------|
| **Combat/Action** | 3 | `savethr.com_1777320323223.jpg`, `savethr.com_1777320351002.jpg`, `savethr.com_1777320353495.jpg` |
| **Portrait/Character** | 5 | `savethr.com_1777320349016.jpg`, `savethr.com_1777320358328.jpg`, `savethr.com_1777320360190.jpg`, `673872296_*`, `682679537_*` |
| **Landscape/Atmosphere** | 4 | `pexels-ambient_nature_*` (×3), `QuietSpringAfternoon-noLogo.jpg` |
| **Anime/Stylized** | 4 | `674546656_*`, `675396080_*`, `682724649_*`, `684280661_*` |
| **SciFi/Abstract** | 3 | `2688x1485.png`, `3840x2100.png`, `threadsdownloader.com_6cf192.jpeg` |
| **Other** | 1 | `savethr.com_1777320355898.jpg` |

---

## 12. OPEN QUESTIONS

1. **Should we switch to plain-text captions (no JSON)?** — Would avoid model hallucination but lose structured data.
2. **Should we get a USB headset or fix Bluetooth for voice input?** — Hardware decision, not technical.
3. **Should we try Qwen2 VL 7B despite slower speed for better JSON reliability?** — 7B is ~3x slower but more reliable structured output.
4. **Should we add more images to the library (current: 20)?** — More images = better search coverage but longer indexing.
5. **Should we implement a relevance ranking score?** — Currently no ranking, just boolean match.

---

## 13. ONE-PAGE CHEAT SHEET

```
WHAT FRIDAY DOES:
  Type query → search local captions → open matching images on XP-Pen

WHAT WORKS NOW:
  ✓ Text input pipeline
  ✓ Auto-detect LM Studio IP
  ✓ Multiple tiled windows on XP-Pen
  ✓ Keyword search (instant, local)

WHAT'S BROKEN:
  ✗ Exact-word search only (misses partial matches)
  ✗ 3 images have broken captions
  ✗ Voice input (no mic hardware)
  ✗ Model hallucinates JSON

NEXT 3 STEPS:
  1. Fix search to substring matching
  2. Fix 3 broken captions
  3. Test random words

DEADLINE: June 1, 2026 (15 days left)
CONFIDENCE: HIGH if voice deprioritized
```

---

*Generated: 2026-05-16 | Session 4 | This document is the single source of truth for Friday's development state.*
