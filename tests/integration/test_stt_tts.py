"""
Real STT -> TTS integration test.

This test uses the project's actual reference audio and real models.
It is intentionally marked as slow because STT/TTS inference is expensive.
"""

from pathlib import Path

import pytest

from stt.stt import get_stt_output
from tts.tts import TTSWrapper


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUDIO_PATH = PROJECT_ROOT / "reference_clips" / "speaker_en.wav"
SPEAKER_WAV = PROJECT_ROOT / "reference_clips" / "speaker_en.wav"
OUTPUT_PATH = PROJECT_ROOT / "tests" / "integration" / "test_integration_output.wav"


@pytest.mark.slow
def test_stt_to_tts():
    # Make sure the test input actually exists.
    assert AUDIO_PATH.exists(), f"Missing test audio: {AUDIO_PATH}"
    assert SPEAKER_WAV.exists(), f"Missing speaker reference: {SPEAKER_WAV}"

    # Step 1: real STT
    stt_result = get_stt_output(str(AUDIO_PATH))

    assert stt_result.text.strip(), "STT returned empty text"
    assert stt_result.language in {"en", "hi"}

    # Step 2: pass STT output into real TTS
    wrapper = TTSWrapper()
    wrapper.preload_speakers({"en": str(SPEAKER_WAV)})

    out_path = wrapper.synthesize_auto(
        text=stt_result.text,
        speaker_wav=str(SPEAKER_WAV),
        language_hint=stt_result.language,
        out_path=str(OUTPUT_PATH),
    )

    # Step 3: verify TTS actually produced an output file
    assert out_path is not None
    assert Path(out_path).exists(), f"TTS output not created: {out_path}"

    print(f"\nDetected language: {stt_result.language}")
    print(f"Transcribed text: {stt_result.text}")
    print(f"Synthesized audio: {out_path}")