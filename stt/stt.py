from typing import List, Tuple
import os
import sys
import threading

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from faster_whisper import WhisperModel
from contracts.schemas import SttOutput


# ---------------------------------------------------------
# Model configuration
# ---------------------------------------------------------

_model = None
_ALLOWED_MODEL_SIZES = {"tiny", "base", "small", "medium", "large-v3"}
_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")

if _MODEL_SIZE not in _ALLOWED_MODEL_SIZES:
    print(f"WARNING: WHISPER_MODEL_SIZE='{_MODEL_SIZE}' is unsupported. "
          f"Expected one of {sorted(_ALLOWED_MODEL_SIZES)}. Falling back to 'small'.",
          file=sys.stderr)
    _MODEL_SIZE = "small"


# ---------------------------------------------------------
# One-slot cache
#
# FIX (STT Lead): the previous version used `_last_key = None` to mean BOTH
# "last call had no audio (mock mode)" AND "last call was a raw in-memory
# array" (arrays aren't hashable/comparable cheaply, so that branch stored the
# object itself in `_last_audio` and left `_last_key` as a placeholder None).
# Those two cases are indistinguishable once `_last_key` is None, so calling
# transcribe(None) right after transcribing a real numpy array would silently
# return the real array's cached transcription instead of the mock sentence.
#
# Fix: tag every cache entry with an explicit `kind` so "no audio", "file
# path", and "in-memory array" can never be confused with each other.
# ---------------------------------------------------------

_last_signature = None   # (kind, ...details, language_hint) or None
_last_result = None
_cache_lock = threading.Lock()  # guards the cache against concurrent FastAPI requests


def _signature(audio_chunk, language_hint):
    if audio_chunk is None:
        return ("none", language_hint)
    if isinstance(audio_chunk, str):
        try:
            mtime = os.path.getmtime(audio_chunk)
        except OSError:
            mtime = None
        return ("path", audio_chunk, mtime, language_hint)
    # In-memory audio (e.g. a numpy array from live mic capture). id() can
    # theoretically be reused after garbage collection, but the only case we
    # need to handle is "the exact same call happening twice in a row" (e.g.
    # detect_language() then transcribe() on the same chunk) — good enough
    # for a single-user demo; not claiming this is a general-purpose cache.
    return ("object", id(audio_chunk), language_hint)


# ---------------------------------------------------------
# Day-1 mock data — matches tests/test_contracts.py's allocator test sentence
# ---------------------------------------------------------

_MOCK_LANGUAGE = "en"
_MOCK_WORDS = ["Send", "backup", "to", "grid", "reference", "4729"]
_MOCK_CONFIDENCE = [0.98, 0.95, 0.90, 0.60, 0.55, 0.40]


def _get_model():
    global _model
    if _model is None:
        try:
            _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
        except Exception as e:
            raise RuntimeError(f"Failed to load faster-whisper model '{_MODEL_SIZE}': {e}") from e
    return _model


def _run_model(audio_chunk, language_hint=None):
    """Runs faster-whisper once per distinct (audio, language_hint) and caches
    the result. Returns: (language, words: list[str], confidence_per_word: list[float])

    language_hint: optional ISO-639-1 code (e.g. "en", "hi") to skip
    auto-detection when you already know which language is being spoken.
    NOTE: not validated against a fixed list here — this repo hasn't pinned
    down the two demo languages in any shared doc, so guessing and hardcoding
    a set would risk rejecting a perfectly valid hint. faster-whisper itself
    will raise a clear error if given a code it doesn't recognize.
    """
    global _last_signature, _last_result

    if language_hint is not None:
        if not isinstance(language_hint, str):
            raise ValueError(
                f"language_hint must be 'en' or 'hi', got {language_hint!r}"
            )

        language_hint = language_hint.strip().lower()

        if language_hint not in {"en", "hi"}:
            raise ValueError(
                f"language_hint must be 'en' or 'hi', got {language_hint!r}"
            )

    sig = _signature(audio_chunk, language_hint)

    with _cache_lock:
        if sig == _last_signature and _last_result is not None:
            return _last_result

        if audio_chunk is None:

            mock_language = (
                language_hint
                if language_hint
                else _MOCK_LANGUAGE
            )

            result = (
                mock_language,
                list(_MOCK_WORDS),
                list(_MOCK_CONFIDENCE)
            )
        else:
            if isinstance(audio_chunk, str) and not os.path.isfile(audio_chunk):
                raise FileNotFoundError(f"Audio file not found: {audio_chunk}")
            try:
                model = _get_model()
                kwargs = {"word_timestamps": True}
                if language_hint:
                    kwargs["language"] = language_hint
                segments, info = model.transcribe(audio_chunk, **kwargs)
                words: List[str] = []
                confidences: List[float] = []
                for segment in segments:
                    for word in segment.words:
                        w = word.word.strip()
                        if w:  # skip empty tokens (e.g. stray punctuation-only entries)
                            words.append(w)
                            confidences.append(float(word.probability))  # native float, not numpy float32
                result = (info.language, words, confidences)
            except FileNotFoundError:
                raise
            except Exception as e:
                raise RuntimeError(f"STT transcription failed: {e}") from e

        _last_signature, _last_result = sig, result
        return result


def transcribe(audio_chunk, language_hint=None) -> Tuple[str, List[float]]:
    """
    Args:
        audio_chunk: WAV file path, numpy float32 array, or None (Day-1 mock —
                     see module docstring in earlier versions for why).
        language_hint: optional known language code to skip auto-detection.
    Returns: (text, confidence_per_token) — matches contracts/schemas.py::SttOutput
    """
    _language, words, confidences = _run_model(audio_chunk, language_hint=language_hint)
    return " ".join(words), confidences


def detect_language(audio_chunk) -> str:
    language, _words, _confidences = _run_model(
        audio_chunk
    )
    return language


def get_stt_output(audio_chunk, language_hint=None) -> SttOutput:
    """Convenience wrapper returning the validated contracts.schemas.SttOutput
    object directly. Not called by main.py/api.py yet (they build the response
    manually) — safe to ignore unless you want the extra validation."""
    language, words, confidence = _run_model(audio_chunk, language_hint=language_hint)
    text = " ".join(words)
    return SttOutput(language=language, text=text, tokens=text.split(), confidence_per_token=confidence)


# ---------------------------------------------------------
# STT evaluation scaffold — fill TEST_CASES with real recordings before your
# demo-language testing step. Deliberately left empty; no fabricated results.
# ---------------------------------------------------------

TEST_CASES: List[Tuple[str, str, str]] = [
    # (audio_path, expected_text, language_label)
    # ("stt/samples/en_1.wav", "exact expected transcript", "en"),
]


def run_stt_eval(cases: List[Tuple[str, str, str]] = None) -> None:
    cases = cases if cases is not None else TEST_CASES
    if not cases:
        print("No STT test cases provided. Populate TEST_CASES with real "
              "demo-language sentences, expected transcripts, and audio paths.")
        return
    print("\n=== STT EVALUATION ===")
    for audio_path, expected_text, language_label in cases:
        try:
            actual_text, _confidences = transcribe(audio_path)
            verdict = "PASS" if actual_text.strip() == expected_text.strip() else "FAIL"
        except (FileNotFoundError, RuntimeError) as e:
            actual_text, verdict = f"<ERROR: {e}>", "FAIL"
        print(f"\n[{language_label}] {audio_path}\n  Expected: {expected_text}\n  Actual:   {actual_text}\n  Result:   {verdict}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        result = get_stt_output(path)
        print("\n=== STT CONTRACT OUTPUT ===")
        print(result.model_dump())
        if path is None:
            print("\n(No file given — this is mock output. Run: python stt.py path/to/test.wav)")
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)