"""
TTS Wrapper — Coqui XTTS v2
Day 1 deliverable: TTS Lead

Goal for today (per build plan):
  1. Wrap pretrained XTTS v2.
  2. Get voice-cloning conditioning working (reference clip -> speaker_embedding).
  3. Confirm basic prosody (i.e. output isn't flat/robotic).
  4. Explicitly test BOTH demo languages — don't assume XTTS v2 handles them
     cleanly just because they're "in the docs". Coqui's multilingual coverage
     has shifted across releases, so this script prints what YOUR installed
     version actually reports before trusting it.

Known, accepted caveat (documented, not hidden — same policy as the tagger):
  check_prosody() below is a CHEAP heuristic (pitch/energy variance), not a
  perceptual quality score. It only proves the output isn't monotone/robotic.
  It does NOT prove the cloned voice actually sounds like the reference
  speaker — that needs a human listening test (Day 4 checklist item), not a
  script number.

License note (flag to the team, not a blocker for a hackathon demo):
  XTTS v2 ships under Coqui's CPML license, which restricts commercial use.
  Fine for SIH demo/roadmap purposes — just don't claim "production-ready"
  on the pitch deck without noting this.
"""

import os
import json
import base64
import numpy as np
import librosa
from TTS.api import TTS

# TODO: confirm against your actual rehearsed demo languages / contracts/interfaces.md
DEMO_LANGUAGES = ["en", "hi"]

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


class TTSWrapper:
    def __init__(self, device: str = "cpu"):
        print("Loading Coqui XTTS v2 model...")
        self.tts = TTS(MODEL_NAME).to(device)
        self._verify_supported_languages()

    def _verify_supported_languages(self):
        """
        Don't trust the README — trust what THIS install reports. Hindi support
        in particular was added later than several other languages in XTTS v2's
        history, so this check is not optional.
        """
        langs = None
        try:
            langs = self.tts.languages
        except Exception as e:
            print(f"[WARN] Could not read supported languages from model: {e}")

        print(f"[TTS] Model reports supported languages: {langs}")
        for lang in DEMO_LANGUAGES:
            if langs and lang not in langs:
                print(f"[WARNING] '{lang}' is NOT in this install's reported language list. "
                      f"Do not assume it will work — the test block below will tell you for sure.")

    def synthesize(self, text: str, language: str, speaker_wav: str, out_path: str = None) -> str:
        """
        text: reconstructed transcript text
        language: e.g. 'en' or 'hi' — must be in DEMO_LANGUAGES
        speaker_wav: path to a short (6-10s), clean, single-speaker reference clip
                     — this IS the "speaker_embedding" input per the contract;
                     XTTS computes the embedding internally from this clip.
        """
        if language not in DEMO_LANGUAGES:
            raise ValueError(f"Language '{language}' not in DEMO_LANGUAGES={DEMO_LANGUAGES}")
        if not os.path.exists(speaker_wav):
            raise FileNotFoundError(f"Reference speaker clip not found: {speaker_wav}")

        if out_path is None:
            out_path = f"_tmp_tts_out_{language}.wav"

        self.tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=out_path,
        )
        return out_path

    def to_packet_format(self, wav_path: str) -> dict:
        """
        Rough draft of what the Backend Lead will likely want for base64-over-HTTP.
        RENAME FIELDS to match contracts/schemas.py once you've read it with the team.
        """
        audio, sr = librosa.load(wav_path, sr=None)
        with open(wav_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {
            "audio_base64": b64,
            "sample_rate": sr,
            "duration_sec": round(len(audio) / sr, 2),
        }

    def check_prosody(self, wav_path: str) -> dict:
        """
        Cheap sanity check only — see module docstring for what this does NOT prove.
        Flags monotone/robotic output via pitch (F0) variance across the clip.
        """
        y, sr = librosa.load(wav_path, sr=None)
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7")
        )
        f0_voiced = f0[voiced_flag] if voiced_flag is not None else np.array([])
        energy = librosa.feature.rms(y=y)[0]

        return {
            "pitch_mean_hz": float(np.nanmean(f0_voiced)) if len(f0_voiced) else None,
            "pitch_std_hz": float(np.nanstd(f0_voiced)) if len(f0_voiced) else None,
            "energy_mean": float(np.mean(energy)),
            "energy_std": float(np.std(energy)),
            # heuristic threshold — tune after listening to a few real outputs
            "flag_monotone": bool(len(f0_voiced) and np.nanstd(f0_voiced) < 5.0),
        }


if __name__ == "__main__":
    """
    Self-test — mirrors the Allocator Lead's approach: test real sentences per
    language, including the actual critical-word sentence, not just a filler
    happy-path line. Requires a short reference clip per language/speaker in
    ./reference_clips/ (record 6-10s of clear, quiet-room speech per speaker).
    """
    wrapper = TTSWrapper()

    test_sentences = {
        "en": [
            "We need help at grid reference two eight point five north.",  # critical-word sentence
            "The weather is good today.",                                  # neutral control
        ],
        "hi": [
            "हमें मदद चाहिए।",     # critical Hindi sentence
            "आज मौसम अच्छा है।",   # neutral Hindi control
        ],
    }

    reference_clips = {
        "en": "reference_clips/speaker_en.wav",
        "hi": "reference_clips/speaker_hi.wav",  # reuse same file if it's one speaker/voice
    }

    results = []
    for lang, sentences in test_sentences.items():
        for sentence in sentences:
            try:
                out_path = wrapper.synthesize(sentence, lang, reference_clips[lang])
                prosody = wrapper.check_prosody(out_path)
                status = "OK"
            except Exception as e:
                prosody = None
                status = f"FAILED: {e}"
            results.append({"lang": lang, "text": sentence, "status": status, "prosody": prosody})

    print(json.dumps(results, indent=2, ensure_ascii=False))