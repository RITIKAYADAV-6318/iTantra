"""
STT module — owner: [STT Lead name]

Contract: contracts/schemas.py::SttOutput
    transcribe(audio_chunk) -> (text: str, confidence_per_token: list[float])

DECISION LOG (Day 1): Using faster-whisper instead of AI4Bharat IndicConformer.
IndicConformer requires NVIDIA NeMo (AI4Bharat's own fork), which needs a Linux/WSL
setup and a non-trivial `reinstall.sh` build — high risk to fight on Day 1.
faster-whisper satisfies the exact same contract, already returns real per-word
confidence via `word.probability`, and installs with a plain `pip install`.

Swappable later without touching anything downstream — only this file's internals
change; everyone else only depends on transcribe()'s signature, which stays the same.
If someone gets IndicConformer working on a Linux/WSL box later, swap it in here and
nothing else in the repo needs to change.
"""

from typing import List, Tuple
import os
from faster_whisper import WhisperModel

_model = None

# Configurable via env var so you can A/B test "small" vs "medium" against your
# actual rehearsed demo sentences without editing code each time:
#   WHISPER_MODEL_SIZE=medium python stt.py test.wav
_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")


def _get_model():
    global _model
    if _model is None:
        # Decision rule: test both "small" and "medium" against your actual demo
        # sentences (see docs/BUILD_PLAN.md). If "small" gets the critical
        # word (number/name/coordinate) right every time, keep it — no reason to
        # pay the latency cost. If it fumbles even once, use "medium" instead;
        # a couple extra seconds is a fine trade for not breaking the core demo
        # moment. Don't guess — measure it on your rehearsed sentences.
        _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_chunk) -> Tuple[str, List[float]]:
    """
    Args:
        audio_chunk: path to a WAV file, or a numpy float32 array — faster-whisper
                     accepts either.
    Returns:
        text: transcribed text
        confidence_per_token: one confidence score [0,1] per word, aligned with
                               text.split() — matches contracts/schemas.py::SttOutput
    """
    model = _get_model()
    segments, _info = model.transcribe(audio_chunk, word_timestamps=True)

    words = []
    confidences = []
    for segment in segments:
        for word in segment.words:
            words.append(word.word.strip())
            confidences.append(word.probability)

    text = " ".join(words)
    return text, confidences


def detect_language(audio_chunk) -> str:
    """Language ID via faster-whisper's built-in language detection."""
    model = _get_model()
    _segments, info = model.transcribe(audio_chunk, word_timestamps=False)
    return info.language


if __name__ == "__main__":
    # Quick manual test: python stt.py path/to/test.wav
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        text, conf = transcribe(path)
        print(f"Text: {text}")
        print(f"Confidence: {conf}")
    else:
        print("Usage: python stt.py <path_to_wav_file>")
