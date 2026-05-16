# AGENTS.md — Friday Project Context

## What This Project Is
Friday is a terminal-native, local-first AI agent for visual artists on Fedora 44. It retrieves reference images from a personal library using voice commands and semantic search.

## Hardware Constraints
- AMD Ryzen 5 5600X, Intel Arc A750, 16GB RAM
- No heavy GPU compute. Everything must run locally or via LM Studio on this machine.
- Terminal-first, headless approach. No GUI frameworks.

## Approved Stack (Locked In)
- **Voice:** Vosk (offline, local)
- **Backend:** Python 3.x
- **Image Display:** feh or imv (terminal-spawned image viewers)
- **Search:** CLIP embeddings + FAISS index
- **Vision-Language Model:** Qwen2-VL-2B-Instruct via LM Studio (2 concurrent slots)
- **Index Format:** Plain-text descriptors with CHARACTER / ENVIRONMENT / COLOR line prefixes (NOT JSON — the model hallucinates JSON but writes excellent plain text)

## Core Flow
1. User speaks a command (e.g., "dark forest with a hooded figure")
2. Vosk transcribes to text
3. Text is matched against indexed descriptors via substring search
4. CLIP+FAISS retrieves top-k image paths
5. feh/imv opens the results

## Current State
- **Working files:** `friday_text.py`, `search_friday.py`, `reindex_all.py`
- **Dead code:** 23 files from failed experiments clutter the repo. These should be removed or moved to an `archive/` folder.
- **Missing:** Vosk voice pipeline is not yet integrated. The indexer runs, search works, but voice input is stubbed/pending.
- **MVP Deadline:** June 1, 2026

## Code Style & Rules
- Keep it simple. Friday is an MVP. Do not over-engineer.
- No PyQt6, no KRunner, no transparent overlays, no cursor pets, no persistent mascots, no local LLM inference beyond LM Studio, no Obsidian integration.
- Prefer subprocess calls to existing tools (feh, imv) over building custom UI.
- The indexer must output plain text with line prefixes, never JSON.
- All search matching uses substring search, not regex.

## File Structure (Desired)
```
friday/
├── friday.py          # Main entry point (voice → search → display)
├── search.py          # Search engine (CLIP + FAISS + text index)
├── indexer.py         # Re-indexing script (VL model → plain text descriptors)
├── config.py          # Paths, model endpoints, constants
├── archive/           # Dead experiments (preserved but out of the way)
├── index/             # FAISS index + metadata
└── AGENTS.md          # This file
```

## Testing Approach
- Test voice pipeline with a short WAV file before integrating live mic.
- Test search with known image paths to verify FAISS retrieval.
- Test display by verifying feh/imv actually opens with the returned paths.
