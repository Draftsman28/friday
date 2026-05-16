# Friday Project Roadmap
## Beginner → Intermediate → Expert

---

## TIER 1: BEGINNER (MVP — Complete by June 1)

**Goal:** Speak a word, see an image. Nothing else.

### What Already Works
- `captions_expert.json` — 20 captions indexed
- `search_vl_expert.py` — keyword search works
- LM Studio + Qwen2 VL 2B — running at 10.146.227.181:1234

### What You Need To Do (2 hours max)

#### 1. Install Vosk dependencies
```bash
pip install vosk sounddevice numpy
```

#### 2. Download Vosk model (~40MB)
```bash
mkdir -p ~/friday/models
cd ~/friday/models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

#### 3. Copy beginner scripts
```bash
cp /mnt/agents/output/listen.py ~/friday/core/
cp /mnt/agents/output/friday.py ~/friday/core/
```

#### 4. Test voice input
```bash
python ~/friday/core/listen.py
# Say "warrior" — should print: 📝 Heard: 'warrior'
```

#### 5. Run full pipeline
```bash
python ~/friday/core/friday.py
# Speak → search → feh opens results
```

### Result
You say "dramatic face" → feh opens the closest matching image.

---

## TIER 2: INTERMEDIATE (Week of June 2)

**Goal:** Search by mood, narrative, color — not just object names.

### What You Add
- Re-index 8-12 images with **targeted domain prompts**
  - `combat` domain for fight/training images
  - `portrait` domain for face/character images
  - `atmosphere` domain for environment/lighting images
- `search_multi_lens_llm.py` — LLM expands "tense" into "tension, anxiety, conflict, strain"
- `friday.py` updated to accept `--lens narrative` flag

### Commands
```bash
# Re-index only the images that matter
python ~/friday/core/index_targeted.py --domain combat --files batman.jpg warrior.png
python ~/friday/core/index_targeted.py --domain portrait --files face.jpg character.png

# Search with expansion
python ~/friday/core/search_multi_lens_llm.py --lens narrative "intense training"
```

### Result
You say "tense training scene with dramatic shadows" → gets the right image even if captions don't use those exact words.

---

## TIER 3: EXPERT (June onward — as needed)

**Goal:** Production-grade art reference pipeline.

### What You Add
- Full multi-lens concurrent indexer for bulk new images
- CLIP embeddings for true semantic similarity (optional)
- Custom domain prompts for your specific art style
- Batch overnight indexing: drop folder → auto-index by morning
- Tablet integration: pen button triggers Friday voice search
- Query reranking: LLM reads top 5 candidates, reorders by true relevance

### Result
Professional workflow: draw → hit pen button → say "reference for hand holding sword at sunset" → best match appears.

---

## CRITICAL RULE

**Do NOT work on Tier 2/3 until Tier 1 is working.**

You are currently stuck re-indexing, testing prompts, and chasing quality — but you can't even say "Friday, find warriors" yet. 

**Get the voice pipeline working first. Then make it smarter.**
