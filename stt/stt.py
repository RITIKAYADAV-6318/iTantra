from typing import List, Tuple
import os
import sys
from threading import Lock
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from faster_whisper import WhisperModel
from contracts.schemas import SttOutput


# ---------------------------------------------------------
# Model configuration
# ---------------------------------------------------------

_model = None

_ALLOWED_MODEL_SIZES = {
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
}

_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")

if _MODEL_SIZE not in _ALLOWED_MODEL_SIZES:
    print(
        f"WARNING: WHISPER_MODEL_SIZE='{_MODEL_SIZE}' is unsupported. "
        f"Expected one of {sorted(_ALLOWED_MODEL_SIZES)}. "
        f"Falling back to 'small'.",
        file=sys.stderr,
    )
    _MODEL_SIZE = "small"


# ---------------------------------------------------------
# One-slot cache
# ---------------------------------------------------------

_last_audio = None
_last_key = None
_last_result = None


# ---------------------------------------------------------
# Day-1 mock data
# ---------------------------------------------------------

_MOCK_LANGUAGE = "en"

_MOCK_WORDS = [
    "Send",
    "backup",
    "to",
    "grid",
    "reference",
    "4729",
]

_MOCK_CONFIDENCE = [
    0.98,
    0.95,
    0.90,
    0.60,
    0.55,
    0.40,
]


# ---------------------------------------------------------
# Load Whisper model
# ---------------------------------------------------------

def _get_model():
    global _model

    if _model is None:
        try:
            _model = WhisperModel(
                _MODEL_SIZE,
                device="cpu",
                compute_type="int8",
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load faster-whisper model "
                f"'{_MODEL_SIZE}': {e}"
            ) from e

    return _model


# ---------------------------------------------------------
# Cache check
# ---------------------------------------------------------

def _cache_hit(audio_chunk) -> bool:
    if _last_result is None:
        return False

    if audio_chunk is None:
        return _last_key is None

    if isinstance(audio_chunk, str):

        if not os.path.isfile(audio_chunk):
            return False

        current_key = (
            audio_chunk,
            os.path.getmtime(audio_chunk)
        )

        return current_key == _last_key

    return audio_chunk is _last_audio


_cache_lock = Lock()

_last_audio = None
_last_key = None
_last_result = None

# ---------------------------------------------------------
# Run Whisper
# ---------------------------------------------------------

def _run_model(audio_chunk):
    global _last_audio
    global _last_key
    global _last_result

 with _cache_lock:

    if isinstance(audio_chunk, str):

        _last_audio = None

        _last_key = (
            audio_chunk,
            os.path.getmtime(audio_chunk)
        )

    else:

        _last_audio = audio_chunk
        _last_key = None

    _last_result = result

    return result

    # Validate file path
    if isinstance(audio_chunk, str):
        if not os.path.isfile(audio_chunk):
            raise FileNotFoundError(
                f"Audio file not found: {audio_chunk}"
            )

    try:
        model = _get_model()

        segments, info = model.transcribe(
            audio_chunk,
            word_timestamps=True,
        )

        words: List[str] = []
        confidences: List[float] = []

        for segment in segments:
            for word in segment.words:

                current_word = word.word.strip()

                if current_word:
                    words.append(current_word)
                    confidences.append(
                        float(word.probability)
                    )

        result = (
            info.language,
            words,
            confidences,
        )

    except FileNotFoundError:
        raise

    except Exception as e:
        raise RuntimeError(
            f"STT transcription failed: {e}"
        ) from e

    if isinstance(audio_chunk, str):

        _last_audio = None

        _last_key = (
            audio_chunk,
            os.path.getmtime(audio_chunk)
        )

    else:

        _last_audio = audio_chunk
        _last_key = None

    _last_result = result

    return result


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def transcribe(audio_chunk,language_hint=None) -> Tuple[str, List[float]]:
    """
    Contract:
        transcribe(audio_chunk)
        -> (text, confidence_per_token)

    Note:
        confidence_per_token is word-level confidence
        in this implementation.
    """

    _language, words, confidences = _run_model(audio_chunk)

    text = " ".join(words)

    return text, confidences


def detect_language(audio_chunk) -> str:
    """
    Contract:
        detect_language(audio_chunk)
        -> language
    """

    language, _words, _confidences = _run_model(audio_chunk)

    return language


# ---------------------------------------------------------
# STT -> Allocator Contract Object
# ---------------------------------------------------------

def get_stt_output(audio_chunk) -> SttOutput:
    """
    Returns validated output matching
    contracts.schemas.SttOutput
    """

    language = detect_language(audio_chunk)

    text, confidence = transcribe(audio_chunk)

    tokens = text.split()

    return SttOutput(
        language=language,
        text=text,
        tokens=tokens,
        confidence_per_token=confidence,
    )


# ---------------------------------------------------------
# Manual testing
# ---------------------------------------------------------

if __name__ == "__main__":

    path = sys.argv[1] if len(sys.argv) > 1 else None

    try:

        result = get_stt_output(path)

        print("\n=== STT CONTRACT OUTPUT ===")
        print(result.model_dump())

        if path is None:
            print(
                "\n(No file given — this is mock output.)"
            )
            print(
                "Run: python stt.py path/to/test.wav"
            )

    except FileNotFoundError as e:

        print(
            f"ERROR: {e}",
            file=sys.stderr
        )

        sys.exit(1)

    except RuntimeError as e:

        print(
            f"ERROR: {e}",
            file=sys.stderr
        )

        sys.exit(1)