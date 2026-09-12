"""
Quick STT -> TTS integration test.
Confirms the real handoff works: real audio in, real audio out.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stt.stt import get_stt_output
from tts.tts import TTSWrapper

# ---- CONFIG ----
AUDIO_PATH = r"C:\Users\ritik\OneDrive\Desktop\lovesemm3\iTantra\reference_clips\speaker_en.wav"
SPEAKER_WAV = r"C:\Users\ritik\OneDrive\Desktop\lovesemm3\iTantra\reference_clips\speaker_en.wav"
OUTPUT_PATH = "test_integration_output.wav"
# -----------------

print("\n=== STEP 1: Running STT on real audio ===")
stt_result = get_stt_output(AUDIO_PATH)
print(f"Detected language: {stt_result.language}")
print(f"Transcribed text:  {stt_result.text}")
print(f"Tokens:            {stt_result.tokens}")
print(f"Confidence/token:  {stt_result.confidence_per_token}")

if not stt_result.text.strip():
    print("\n[FAIL] STT returned empty text — nothing to pass to TTS. Stopping.")
    sys.exit(1)

print("\n=== STEP 2: Passing STT's text into TTS ===")
wrapper = TTSWrapper()
wrapper.preload_speakers({"en": SPEAKER_WAV})

out_path = wrapper.synthesize_auto(
    text=stt_result.text,
    speaker_wav=SPEAKER_WAV,
    language_hint=stt_result.language,
    out_path=OUTPUT_PATH,
)

print(f"\n=== DONE ===")
print(f"Original STT text: {stt_result.text}")
print(f"Synthesized audio: {out_path}")
print(f"\nNow LISTEN to {out_path} and compare it against the original recording.")
print("Specifically check: did any numbers/names/coordinates survive both hops intact?")