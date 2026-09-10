"""
TTS module — owner: [TTS Lead name]

Contract: contracts/schemas.py-compatible
    synthesize(text, speaker_embedding, prosody_vector) -> audio (WAV bytes)

DECISION LOG (Day 1): Using Coqui TTS (xtts_v2) instead of AI4Bharat Indic-TTS,
applying the same install-risk check already done for STT. AI4Bharat Indic-TTS is a
separate research toolkit with its own custom setup (repo clone, manual checkpoint
pulls) — lower risk than NeMo, but still more setup than a plain pip install.
Coqui TTS installs with `pip install TTS` on Windows/Mac/Linux with no special
system dependency, and xtts_v2 does voice-cloning-style synthesis from a short
reference clip — which fits the "sounds like the real speaker" USP directly.

VERIFY ON DAY 1 (same as STT's language check): confirm xtts_v2 handles your two
demo languages cleanly on your actual install — Coqui's multilingual language
support has shifted across versions, don't assume, test it against a real sentence
before relying on it for the live demo.

Swappable later without touching anything downstream — only this file's internals
change, everyone else only depends on synthesize()'s signature.
"""

import os
from typing import Optional

_tts = None

# Configurable via env var, same pattern as STT's WHISPER_MODEL_SIZE — lets you
# swap models without editing code.
_MODEL_NAME = os.environ.get("TTS_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2")


def _get_tts():
    global _tts
    if _tts is None:
        from TTS.api import TTS as CoquiTTS
        _tts = CoquiTTS(model_name=_MODEL_NAME, progress_bar=False, gpu=False)
    return _tts


def synthesize(text: str, speaker_embedding: Optional[str] = None,
               prosody_vector: Optional[object] = None, language: str = "en"):
    """
    Args:
        text: text to speak (already reconstructed from received packet)
        speaker_embedding: NOTE — for xtts_v2, this is interpreted as a path to a
                            short reference WAV of the speaker's voice (voice
                            cloning), not an abstract embedding vector. Kept the
                            same parameter name for contract compatibility with
                            other TTS backends that do use a real embedding.
        prosody_vector: not directly used by xtts_v2 (it infers prosody from the
                         reference clip) — kept for contract compatibility, and for
                         a future TTS backend that does take explicit prosody input.
        language: target language code, e.g. "en", "hi"
    Returns:
        audio: WAV bytes
    """
    tts = _get_tts()
    out_path = "_tts_temp_output.wav"
    tts.tts_to_file(
        text=text,
        speaker_wav=speaker_embedding,  # None is valid — falls back to a default voice
        language=language,
        file_path=out_path,
    )
    with open(out_path, "rb") as f:
        audio_bytes = f.read()
    os.remove(out_path)
    return audio_bytes


def extract_speaker_embedding(audio_chunk):
    """For xtts_v2 voice cloning, the 'embedding' is really just a path to a short
    reference clip of the speaker. If audio_chunk is already a file path, this is
    effectively a passthrough — kept as a function so other TTS backends (that do
    real embedding extraction) can implement this properly without changing the
    call site."""
    return audio_chunk if isinstance(audio_chunk, str) else None


def extract_prosody(audio_chunk):
    """Pitch (F0) + energy via librosa — not used by xtts_v2 directly, but kept for
    contract compatibility and for the prosody-distress-detection stretch goal."""
    # STUB — implement with librosa if the distress-detection feature is attempted.
    return None


if __name__ == "__main__":
    # Quick manual test: python tts.py
    audio = synthesize("This is a test sentence.", language="en")
    print(f"Generated audio bytes: {len(audio)}")
