"""
iTantra - Speech-to-Text (STT)

Supports:
- English
- Hindi
- Hinglish / code-switched speech
- Token-level confidence
- Optional explicit language hint
- Mock mode for testing
"""

from __future__ import annotations

import argparse
import os
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from faster_whisper import WhisperModel


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MODEL_SIZE = os.getenv("ITANTRA_WHISPER_MODEL", "small")
DEVICE = os.getenv("ITANTRA_WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("ITANTRA_WHISPER_COMPUTE_TYPE", "int8")

SUPPORTED_LANGUAGES = {"en", "hi"}


# ---------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    """Load and cache the Whisper model."""
    return WhisperModel(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Normalize unnecessary whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def _script_language_label(text: str, detected_language: str) -> str:
    """
    Keep the contract compatible with the current allocator.

    Romanized Hinglish may contain only Latin characters, so script alone
    cannot reliably identify Hindi. In that case, preserve Whisper's
    detected language when it is supported.
    """
    if detected_language in SUPPORTED_LANGUAGES:
        return detected_language

    # Devanagari strongly indicates Hindi.
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    # Default to English for the existing en/hi contract.
    return "en"


def _collect_tokens(segments) -> Tuple[List[str], List[float]]:
    """Collect word tokens and their probabilities."""
    tokens: List[str] = []
    confidences: List[float] = []

    for segment in segments:
        if segment.words:
            for word in segment.words:
                token = word.word.strip()

                if not token:
                    continue

                tokens.append(token)
                confidences.append(float(word.probability))
        else:
           # Fallback when word timestamps are unavailable.
           # avg_logprob is a log-probability (often negative, unbounded) — not a
           # [0,1] confidence score. Convert it to a rough 0-1 estimate so it never
           # violates the STT->Allocator contract's confidence range.
           words = segment.text.strip().split()
           # exp() maps log-probability back to a genuine 0-1 probability-like value.
           import math
           estimated_confidence = max(0.0, min(1.0, math.exp(segment.avg_logprob)))

           for word in words:
            tokens.append(word)
            confidences.append(estimated_confidence)

    return tokens, confidences

def _normalize_tokens_and_confidences(
    tokens: List[str],
    confidences: List[float],
) -> Tuple[List[str], List[float]]:

    merged_tokens = []
    merged_confidences = []

    i = 0

    while i < len(tokens):
        token = tokens[i]

        if (
            i + 1 < len(tokens)
            and token.isdigit()
            and tokens[i + 1].startswith(".")
            and tokens[i + 1][1:].isdigit()
        ):
            merged_tokens.append(token + tokens[i + 1])

            merged_confidences.append(
                min(confidences[i], confidences[i + 1])
            )

            i += 2
            continue

        merged_tokens.append(token)
        merged_confidences.append(confidences[i])

        i += 1

    return merged_tokens, merged_confidences

# ---------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------

def transcribe(
    audio_path: str,
    language: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Transcribe an audio file.

    For Hinglish:
        language=None

    This intentionally enables multilingual decoding so Whisper can
    handle English/Hindi code-switching instead of forcing one language.
    """

    if language is not None and language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Use one of: {sorted(SUPPORTED_LANGUAGES)}"
        )

    model = _get_model()

    # IMPORTANT FOR HINGLISH:
    # Do not force en/hi when no language hint is supplied.
    multilingual = language is None

    segments, info = model.transcribe(
        audio_path,
        language=language,
        multilingual=multilingual,

        # Helps prevent language/context lock-in during code switching.
        condition_on_previous_text=False,

        # Needed for token-level confidence.
        word_timestamps=True,

        # Useful for real-world speech.
        vad_filter=True,
    )

    segments = list(segments)

    tokens, confidences = _collect_tokens(segments)

    tokens, confidences = _normalize_tokens_and_confidences(
        tokens,
        confidences,
    )

    text = " ".join(tokens)

    if not text:
        return "", 0.0

    confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0.0
    )

    return text, float(confidence)


def detect_language(audio_path: str) -> str:
    """
    Detect the dominant language while keeping the existing en/hi contract.

    For Hinglish, this is only a compatibility label.
    The actual transcript remains code-switched.
    """
    model = _get_model()

    segments, info = model.transcribe(
        audio_path,
        multilingual=True,
        condition_on_previous_text=False,
        word_timestamps=False,
        vad_filter=True,
    )

    segments = list(segments)

    text = _clean_text(
        " ".join(segment.text for segment in segments)
    )

    detected = getattr(info, "language", "en")

    return _script_language_label(text, detected)


def get_stt_output(
    audio_path: str,
    language: Optional[str] = None,
):
    """
    Return the STT output in the project's contract format.
    """
    from contracts.schemas import SttOutput

    model = _get_model()

    multilingual = language is None

    segments, info = model.transcribe(
        audio_path,
        language=language,
        multilingual=multilingual,
        condition_on_previous_text=False,
        word_timestamps=True,
        vad_filter=True,
    )

    segments = list(segments)

    text = _clean_text(
        " ".join(segment.text for segment in segments)
    )

    tokens, confidences = _collect_tokens(segments)

    tokens, confidences = _normalize_tokens_and_confidences(
        tokens,
        confidences,
    )

    text = " ".join(tokens)

    detected_language = getattr(info, "language", "en")
    output_language = _script_language_label(
        text,
        detected_language,
    )

    return SttOutput(
        language=output_language,
        text=text,
        tokens=tokens,
        confidence_per_token=confidences,
    )


# ---------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------

def evaluate_stt(
    audio_path: str,
    expected_text: str,
    language: Optional[str] = None,
):
    """Simple WER-style evaluation helper."""
    predicted_text, confidence = transcribe(
        audio_path,
        language=language,
    )

    reference_words = expected_text.lower().split()
    predicted_words = predicted_text.lower().split()

    if not reference_words:
        wer = 0.0 if not predicted_words else 1.0
    else:
        # Levenshtein distance.
        previous = list(range(len(predicted_words) + 1))

        for i, ref_word in enumerate(reference_words, start=1):
            current = [i]

            for j, pred_word in enumerate(predicted_words, start=1):
                substitution = previous[j - 1] + (
                    ref_word != pred_word
                )
                insertion = current[j - 1] + 1
                deletion = previous[j] + 1

                current.append(
                    min(substitution, insertion, deletion)
                )

            previous = current

        wer = previous[-1] / len(reference_words)

    return {
        "predicted_text": predicted_text,
        "expected_text": expected_text,
        "confidence": confidence,
        "wer": wer,
    }


# ---------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------

def mock_transcribe(
    text: str,
    language: str = "en",
):
    """Generate STT output without loading Whisper."""
    from contracts.schemas import SttOutput

    tokens = text.split()

    return SttOutput(
        language=language,
        text=text,
        tokens=tokens,
        confidence_per_token=[1.0] * len(tokens),
    )


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="iTantra Speech-to-Text"
    )

    parser.add_argument(
        "audio",
        nargs="?",
        help="Path to audio file",
    )

    parser.add_argument(
        "--language",
        choices=["en", "hi"],
        default=None,
        help=(
            "Optional language hint. "
            "Leave unset for Hinglish/code-switched speech."
        ),
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock STT instead of Whisper.",
    )

    parser.add_argument(
        "--text",
        default="",
        help="Text to use with --mock.",
    )

    args = parser.parse_args()

    if args.mock:
        result = mock_transcribe(
            args.text,
            args.language or "en",
        )
        print(result.model_dump_json(indent=2))
        return

    if not args.audio:
        parser.error("audio path is required unless --mock is used")

    result = get_stt_output(
        args.audio,
        language=args.language,
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()