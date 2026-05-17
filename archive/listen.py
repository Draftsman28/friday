#!/usr/bin/env python3
"""
Friday Listen — Beginner Tier
Records audio from microphone, uses Vosk for offline speech-to-text.
"""

import json
import wave
import sys
from pathlib import Path

# Try to import vosk
try:
    import vosk
    import sounddevice as sd
    import numpy as np
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install vosk sounddevice numpy")
    sys.exit(1)

MODEL_PATH = str(Path.home() / "friday" / "models" / "vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000

def listen(duration=5):
    """Record audio for N seconds and return transcribed text."""
    if not Path(MODEL_PATH).exists():
        print(f"Vosk model not found: {MODEL_PATH}")
        print("Download: https://alphacephei.com/vosk/models")
        sys.exit(1)

    model = vosk.Model(MODEL_PATH)
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    print(f"🎤 Listening for {duration}s...")

    # Record audio
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype=np.int16)
    sd.wait()

    # Feed to Vosk
    rec.AcceptWaveform(audio.tobytes())
    result = json.loads(rec.Result())
    text = result.get("text", "").strip()

    if text:
        print(f"📝 Heard: '{text}'")
        return text
    else:
        print("🤷 No speech detected")
        return None

if __name__ == "__main__":
    text = listen()
    if text:
        print(text)  # Print so friday.py can capture it
