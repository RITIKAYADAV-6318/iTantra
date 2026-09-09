"""
STT module — owner: [STT Lead name]

Contract (do not change without updating README.md + telling Integration Lead):
    transcribe(audio_chunk) -> (text: str, confidence_per_token: list[float])

Plan:
- Day 1: wrap a pretrained model (Whisper or AI4Bharat IndicConformer) with this signature.
- Day 1: confirm per-token confidence is actually extractable — this feeds the allocator.
- Day 2+: fine-tune on chosen languages if time allows. Pretrained-only is an acceptable
  fallback the whole way through.
"""

from typing import List, Tuple


def transcribe(audio_chunk) -> Tuple[str, List[float]]:
    """
    Args:
        audio_chunk: raw audio (numpy array / bytes / file path — decide with team
                     and document here once fixed).
    Returns:
        text: transcribed text
        confidence_per_token: one confidence score [0,1] per token in `text`,
                               same tokenization the allocator will use.
    """
    # STUB — replace with real model call.
    text = "placeholder transcription"
    confidence_per_token = [1.0] * len(text.split())
    return text, confidence_per_token


def detect_language(audio_chunk) -> str:
    """Lightweight LID. Returns a language code, e.g. 'hi', 'en'."""
    # STUB — replace with real LID model.
    return "en"


if __name__ == "__main__":
    # Quick manual test so anyone can run `python stt.py` and see it work.
    text, conf = transcribe(None)
    print(f"Text: {text}")
    print(f"Confidence: {conf}")
