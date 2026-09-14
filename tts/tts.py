"""
TTS Wrapper — Coqui XTTS v2
TTS Lead deliverable

Goal (per build plan):
  1. Wrap pretrained XTTS v2.
  2. Get voice-cloning conditioning working (reference clip -> speaker_embedding).
  3. Confirm basic prosody (i.e. output isn't flat/robotic).
  4. Explicitly test BOTH demo languages.

Fix history — [FIX 1]-[FIX 11], [FIX 17], [FIX 18] were already implemented
in the previous version. This pass:
  (a) actually implements [FIX 12], [FIX 13], [FIX 14], [FIX 15], [FIX 16],
      which were documented in the old docstring but never written into the
      code — that mismatch is fixed now, docstring matches code.
  (b) adds [FIX 21]-[FIX 23] below, addressing the real bug found today:
      a Hindi sentence was cutting off partway through mid-sentence when
      synthesized as part of a multi-chunk call.

  [FIX 21] ROOT CAUSE, PRIMARY FIX — Unicode normalization on input text.
          The cutoff was traced to malformed Devanagari text reaching
          model.inference() — specifically, text that had passed through a
          terminal/shell that silently dropped combining marks (matras,
          virama) from copy-pasted or retyped Hindi, e.g. "चाहिए" arriving
          as "चाहए". XTTS's text normalizer/tokenizer can behave
          unpredictably (including truncating generation early) on
          malformed input it wasn't trained to expect. Every call to
          synthesize() now runs unicodedata.normalize("NFC", text) up
          front — this fixes decomposed-vs-composed Unicode representation
          issues, though it does NOT fix outright missing characters (if a
          combining mark was actually dropped, not just differently
          encoded, no normalization can restore it). See [FIX 23] for how
          this is caught even when normalization can't fix it.
  [FIX 22] Per-chunk retry with a lower repetition_penalty if a chunk comes
          back suspiciously short relative to its text length. High
          repetition_penalty (2.0, set for demo stage-repeatability) is a
          known XTTS behavior that can trigger early generation stopping,
          independent of the Unicode issue in [FIX 21] — this is a second,
          separate safety net, not a duplicate fix for the same cause.
  [FIX 23] Post-synthesis duration sanity check (this is the [FIX 14] that
          was documented but never implemented before). Warns loudly
          — does not raise, so a rehearsal run isn't killed — if final
          output duration is suspiciously short for the input text length,
          in either language. This is what would have caught today's bug
          immediately instead of requiring a manual listen to notice it.

  [FIX 12] (implemented now) to_packet_format()/to_packet_format_from_memory()
          include "audio_format": "wav". contracts/schemas.py may name this
          field differently — VERIFY against the actual file; this is a
          best-effort guess, not a confirmed contract match.
  [FIX 13] (implemented now) Empty/whitespace-only text raises ValueError
          immediately instead of reaching model.inference() with "".
  [FIX 15] (implemented now) synthesize_array() does the actual inference
          and returns (wav, sr) in memory; synthesize() wraps it and writes
          to disk. Gives to_packet_format_from_memory() a real producer.
  [FIX 16] (implemented now) Default output path for synthesize()'s scratch
          files and compare_numeral_forms()'s check files now live under
          tempfile.gettempdir()/itantra_tts/, not the working directory.
          bake_demo_fallback()'s output is intentionally kept in
          demo_fallback/ (not temp) since that's a real deliverable asset.

  [FIX 28] Added synthesize_auto() — a convenience entry point that routes
          to synthesize() or synthesize_mixed() based on whether the input
          text actually contains mixed scripts (Devanagari + Latin). This
          does NOT change the STT->TTS contract: input/output shapes match
          synthesize()'s exactly. synthesize() and synthesize_mixed() still
          exist unchanged for callers that want explicit control — this is
          an additional convenience method, not a replacement. Rationale:
          the Backend Lead shouldn't need to detect code-switching or know
          this distinction exists; the detection logic (_split_by_language,
          via Devanagari-vs-Latin script checks) already lives in this
          file, so there's no reason to push that decision upstream or add
          a contract field for it.

Known, accepted caveat (documented, not hidden):
  check_prosody() is a CHEAP heuristic (pitch/energy variance), not a
  perceptual quality score. It does NOT prove the cloned voice matches the
  reference speaker — that needs a human listening test.

License note: XTTS v2 ships under Coqui's CPML license (non-commercial).
Fine for an SIH demo — flag on the roadmap slide, don't claim
production-ready.
"""

from utils.ffmpeg_setup import setup_ffmpeg_dlls

setup_ffmpeg_dlls()

import os

os.environ.setdefault("COQUI_TOS_AGREED", "1")

TTS_HOME = os.environ.setdefault(
    "TTS_HOME", os.path.join(os.path.expanduser("~"), "AppData", "Local")
)

import io
import re
import json
import base64
import random
import tempfile
import threading
import unicodedata
import numpy as np
import librosa
import soundfile as sf
import torch
from TTS.api import TTS

_TMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "itantra_tts")
os.makedirs(_TMP_AUDIO_DIR, exist_ok=True)

# TODO: confirm against your actual rehearsed demo languages / contracts/interfaces.md
DEMO_LANGUAGES = ["en", "hi"]

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

INFERENCE_SEED = 42
GENERATION_KWARGS = dict(
    temperature=0.65,
    top_k=50,
    top_p=0.85,
    repetition_penalty=2.0,
)

# [FIX 22] Fallback kwargs used ONLY as a retry when a chunk comes back
# suspiciously short. Lower repetition_penalty trades a little
# take-to-take consistency for a much lower chance of early stopping.
_RETRY_GENERATION_KWARGS = dict(GENERATION_KWARGS, repetition_penalty=1.1)

# Rough heuristic: expect at least this many seconds of audio per character
# of input text, averaged across normal speech. Used only to flag
# suspiciously short output, not as a precise measure — tune after
# listening to a handful of real outputs in both languages.
_MIN_SEC_PER_CHAR = 0.03

_set_seed_lock_note = """
[FIX 10] Global lock around seed-reset + inference. Makes this script safe
to call from multiple threads without racing on torch's global RNG state.
NOT a real fix for concurrent FastAPI requests — it serializes them, which
kills throughput under real concurrency. Backend Lead: if this needs to
handle overlapping requests, either drop deterministic=True for production
calls (keep it only for bake_demo_fallback) or run inference in a
dedicated single worker/queue instead of relying on this lock. [FIX 20]:
if the FastAPI route is `async def` and calls synthesize()/
synthesize_array() directly, this lock blocks the entire event loop for
every concurrent request while inference runs — keep the route a plain
`def` so Starlette's threadpool handles it.
"""
_INFERENCE_LOCK = threading.Lock()

# [FIX 19] Known false-split case: title abbreviations like "Mr. Sharma"
# (period immediately followed by a space) get incorrectly split into two
# chunks. Not fixed — needs a small exception list per language and isn't
# urgent unless your actual demo sentence contains one. Decimals like
# "28.5" are already safe since no whitespace follows that period.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?।])\s+")

# [FIX 24] Code-switched (Hinglish) text support.
#
# LIMITATION, STATED UP FRONT: this detects language PURELY by Unicode
# script (Devanagari vs Latin characters). It has NO way to tell that a
# Latin-script word like "mujhe" or "chahiye" is actually a Hindi word
# transliterated into Roman letters — it will be treated as English and
# likely mispronounced. This only works correctly when Hindi portions of
# the text are written in Devanagari script. VERIFY what your STT
# teammate's actual output looks like for code-switched speech before
# relying on this for the real demo — if Whisper transliterates Hindi to
# Latin script, this approach needs a different (harder) fix: real
# word-level language-ID, not script detection.
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# [FIX 25] Minimum words per language run. Confirmed by testing: a 2-word
# isolated run ("यहाँ है।") synthesized as completely unclear/garbled in
# isolation, even though the SAME words work fine as part of a longer
# utterance. This is a known XTTS limitation on short inputs, not specific
# to Hindi or to this splitting code — no amount of code-level fixing
# changes how XTTS handles short isolated text. The mitigation below
# merges any run shorter than this into a neighboring run rather than
# synthesizing it alone.
_MIN_RUN_WORDS = 3

# [FIX 27] Numeric/critical-content protection. Confirmed by testing: even
# after [FIX 26] correctly routes a Devanagari-containing chunk to
# language="hi", if that SAME chunk also contains spelled-out English
# number words ("two eight point five"), those numbers get mispronounced —
# Hindi's phonemizer doesn't know English number-word vocabulary, same as
# English's phonemizer didn't know Devanagari. There is NO safe merge
# direction once a chunk mixes Devanagari with English number words: both
# language labels break something. Given this project's entire USP is
# protecting exactly this kind of critical numeric content, the fix is to
# NEVER merge a numeric-critical chunk with a different-script neighbor —
# even if that leaves it short and isolated. A mildly awkward-sounding
# isolated number is an acceptable cost; a MISPRONOUNCED number is not.
_NUMBER_WORDS_EN = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "hundred", "thousand", "point",
}
_DIGIT_RE = re.compile(r"\d")


def _contains_protected_numeric(words: list) -> bool:
    for w in words:
        if _DIGIT_RE.search(w):
            return True
        if w.strip(".,;:!?").lower() in _NUMBER_WORDS_EN:
            return True
    return False


def _split_by_language(text: str, min_run_words: int = _MIN_RUN_WORDS) -> list:
    """
    Groups consecutive words of the same script together, then merges any
    run SHORTER than min_run_words into an adjacent run rather than
    synthesizing it in isolation.

    TRADE-OFF, stated explicitly: a merged run is spoken entirely in its
    target neighbor's language. If a short Hindi run gets merged into an
    English neighbor, those few Hindi words will be synthesized with
    English phonetics (likely mispronounced) — but this is a SMALLER
    quality loss than the garbled/unclear output confirmed when a short
    run is synthesized alone. This is a deliberate choice between two
    imperfect options, not a fix that removes the limitation.

    Merge direction: prefers merging into whichever neighbor is LONGER
    (more words), since a longer neighbor run's own clarity is more
    robust to absorbing a couple of extra words. Falls back to whichever
    single neighbor exists at either end of the sentence.

    IMPORTANT CAVEAT unchanged from before: this detects language by
    Unicode SCRIPT only. A Hindi word written in Latin letters (e.g.
    "mujhe") will be treated as English. Verify what your STT teammate's
    actual output looks like for code-switched speech before relying on
    this for the real demo.
    """
    words = text.strip().split()
    if not words:
        return []

    def word_lang(w: str) -> str:
        return "hi" if _DEVANAGARI_RE.search(w) else "en"

    # Pass 1: group consecutive same-language words.
    groups = []  # list of [word_list, lang]
    current_words = [words[0]]
    current_lang = word_lang(words[0])
    for word in words[1:]:
        lang = word_lang(word)
        if lang == current_lang:
            current_words.append(word)
        else:
            groups.append([current_words, current_lang])
            current_words = [word]
            current_lang = lang
    groups.append([current_words, current_lang])

    # Pass 2: repeatedly merge the shortest under-threshold group into its
    # longer neighbor, until no group is left below the threshold or only
    # one group remains. [FIX 27] Numeric-protected groups are SKIPPED
    # entirely here — both as candidates to merge away, and as valid merge
    # targets — since merging numeric content across a script boundary has
    # no safe language label (see _contains_protected_numeric docstring).
    while len(groups) > 1:
        short_idx = next(
            (
                i for i, (w, _lang) in enumerate(groups)
                if len(w) < min_run_words and not _contains_protected_numeric(w)
            ),
            None,
        )
        if short_idx is None:
            break

        def _is_valid_target(idx):
            return idx is not None and 0 <= idx < len(groups) and not _contains_protected_numeric(groups[idx][0])

        left_idx = short_idx - 1 if _is_valid_target(short_idx - 1) else None
        right_idx = short_idx + 1 if _is_valid_target(short_idx + 1) else None

        if left_idx is None and right_idx is None:
            # Only safe neighbors (if any) are numeric-protected — leave
            # this short group isolated rather than risk corrupting a
            # number. Move on; this group stays as its own chunk.
            break

        if left_idx is not None and right_idx is not None:
            target_is_left = len(groups[left_idx][0]) >= len(groups[right_idx][0])
        else:
            target_is_left = left_idx is not None

        short_words, _short_lang = groups[short_idx]
        if target_is_left:
            groups[left_idx][0] = groups[left_idx][0] + short_words
            del groups[short_idx]
        else:
            groups[right_idx][0] = short_words + groups[right_idx][0]
            del groups[short_idx]

    # [FIX 26] Re-assign each FINAL group's language by content, not by
    # whichever neighbor it happened to merge into. A Devanagari word
    # merged into an "en"-labeled chunk corrupted the ENTIRE chunk's
    # synthesis in testing — sending Devanagari under language="en" breaks
    # tokenization for everything in that call. ANY Devanagari character
    # anywhere in a final group forces that whole group to Hindi.
    # [FIX 27] Numeric-protected groups never reach this step with mixed
    # script content in the first place — merging skips them entirely
    # (see pass 2 above) — so this label assignment is safe for them too:
    # a numeric-protected English group has no Devanagari to trigger the
    # override, and stays "en" as intended.
    final_runs = []
    for words_list, _merge_target_lang in groups:
        joined = " ".join(words_list)
        final_lang = "hi" if _DEVANAGARI_RE.search(joined) else "en"
        final_runs.append((joined, final_lang))

    return final_runs


def _set_seed(seed: int = INFERENCE_SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _split_sentences(text: str) -> list:
    parts = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    return parts if parts else [text.strip()]


def _validate_reference_clip(path: str, min_sec: float = 3.0, max_sec: float = 20.0):
    """
    Cheap checks on the reference clip BEFORE latents are computed from it.
    A bad clip (wrong channel count, too short/long, very low sample rate)
    otherwise fails silently — you just get bad-sounding output later with
    no clear cause.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Reference speaker clip not found: {path}")

    info = sf.info(path)

    if info.channels != 1:
        raise ValueError(
            f"Reference clip '{path}' has {info.channels} channels — expected mono (1). "
            f"Re-export as mono before using it for voice cloning."
        )

    duration = info.frames / float(info.samplerate)
    if duration < min_sec or duration > max_sec:
        print(f"[WARNING] Reference clip '{path}' is {duration:.1f}s long — "
              f"recommended range is {min_sec}-{max_sec}s (guideline: 6-10s). "
              f"Cloning may still work, but quality is unverified outside this range.")

    if info.samplerate < 16000:
        print(f"[WARNING] Reference clip '{path}' has a low sample rate "
              f"({info.samplerate} Hz) — this can degrade cloned voice quality. "
              f"Re-record at 16kHz+ if the cloned voice sounds off.")


class TTSWrapper:
    def __init__(self, device: str = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[TTS] Model cache dir: {TTS_HOME}")
        print(f"[TTS] Loading Coqui XTTS v2 model on device='{device}'...")
        _set_seed()
        self.tts = TTS(MODEL_NAME).to(device)
        self.device = device
        self._sample_rate = getattr(self.tts.synthesizer, "output_sample_rate", None) or 24000
        self._verify_supported_languages()
        self._latent_cache = {}

    def _verify_supported_languages(self):
        langs = None
        try:
            langs = self.tts.languages
        except Exception as e:
            print(f"[WARN] Could not read supported languages from model: {e}")

        print(f"[TTS] Model reports supported languages: {langs}")
        for lang in DEMO_LANGUAGES:
            if langs and lang not in langs:
                print(f"[WARNING] '{lang}' is NOT in this install's reported language list. "
                      f"Do not assume it will work — test explicitly.")

    def _get_conditioning_latents(self, speaker_wav: str) -> dict:
        if speaker_wav in self._latent_cache:
            return self._latent_cache[speaker_wav]

        _validate_reference_clip(speaker_wav)

        model = self.tts.synthesizer.tts_model
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=speaker_wav
        )
        latents = {
            "gpt_cond_latent": gpt_cond_latent,
            "speaker_embedding": speaker_embedding,
        }
        self._latent_cache[speaker_wav] = latents
        print(f"[TTS] Cached conditioning latents for speaker clip: {speaker_wav}")
        return latents

    def preload_speakers(self, speaker_wavs: dict):
        """Call once at startup so the first live demo click isn't the one
        paying the latent-computation cost."""
        for lang, path in speaker_wavs.items():
            print(f"[TTS] Preloading speaker latents for '{lang}'...")
            self._get_conditioning_latents(path)

    # ------------------------------------------------------------------
    # Core synthesis
    # ------------------------------------------------------------------
    def _infer_one(self, text: str, language: str, latents: dict, kwargs: dict) -> np.ndarray:
        model = self.tts.synthesizer.tts_model
        out = model.inference(
            text=text,
            language=language,
            gpt_cond_latent=latents["gpt_cond_latent"],
            speaker_embedding=latents["speaker_embedding"],
            **kwargs,
        )
        wav = out["wav"] if isinstance(out, dict) and "wav" in out else out
        return np.asarray(wav)

    def _infer_chunk_with_retry(self, chunk: str, language: str, latents: dict) -> np.ndarray:
        """
        [FIX 22] Generates one chunk. If the result looks suspiciously short
        for the chunk's text length, retries ONCE with a lower
        repetition_penalty (early-stopping risk drops significantly at
        repetition_penalty~1.1 vs 2.0). Logs loudly either way so a short
        result is never silent.
        """
        wav = self._infer_one(chunk, language, latents, GENERATION_KWARGS)
        expected_min_sec = len(chunk) * _MIN_SEC_PER_CHAR
        actual_sec = len(wav) / self._sample_rate

        if actual_sec < expected_min_sec:
            print(f"[WARNING] Chunk output looks short: {actual_sec:.2f}s for "
                  f"{len(chunk)} chars ({chunk!r}). Retrying with lower "
                  f"repetition_penalty...")
            retry_wav = self._infer_one(chunk, language, latents, _RETRY_GENERATION_KWARGS)
            retry_sec = len(retry_wav) / self._sample_rate
            if retry_sec > actual_sec:
                print(f"[TTS] Retry produced longer output ({retry_sec:.2f}s vs "
                      f"{actual_sec:.2f}s) — using retry result.")
                return retry_wav
            print(f"[WARNING] Retry did not improve length ({retry_sec:.2f}s). "
                  f"Keeping original — this chunk may genuinely be truncated. "
                  f"Listen to the output and consider rephrasing this text if so.")
        return wav

    def synthesize_array(self, text: str, language: str, speaker_wav: str,
                          deterministic: bool = True) -> tuple:
        """
        [FIX 15] Does the actual inference and returns (wav: np.ndarray, sr: int)
        in memory, with no disk write. synthesize() wraps this for the
        common "give me a file" case.
        """
        if language not in DEMO_LANGUAGES:
            raise ValueError(f"Language '{language}' not in DEMO_LANGUAGES={DEMO_LANGUAGES}")

        # [FIX 13] Fail loudly on empty input instead of reaching inference with "".
        if not text or not text.strip():
            raise ValueError("synthesize_array() received empty or whitespace-only text.")

        # [FIX 21] Normalize Unicode BEFORE anything else touches the text.
        # Fixes decomposed-vs-composed representation mismatches that can
        # reach the tokenizer as malformed input (traced root cause of a
        # Hindi sentence cutting off mid-way). Does not restore genuinely
        # missing combining marks — see [FIX 23] for catching that case.
        text = unicodedata.normalize("NFC", text)

        latents = self._get_conditioning_latents(speaker_wav)
        chunks = _split_sentences(text)

        wav_segments = []
        with _INFERENCE_LOCK:
            for chunk in chunks:
                if deterministic:
                    _set_seed()
                wav_segments.append(self._infer_chunk_with_retry(chunk, language, latents))

        wav = np.concatenate(wav_segments) if len(wav_segments) > 1 else wav_segments[0]

        # [FIX 23] Post-synthesis sanity check on the FULL output, not just
        # per-chunk — catches issues that only show up after concatenation.
        expected_min_sec = len(text) * _MIN_SEC_PER_CHAR
        actual_sec = len(wav) / self._sample_rate
        if actual_sec < expected_min_sec:
            print(f"[WARNING] Final synthesized audio is {actual_sec:.2f}s for "
                  f"{len(text)} input characters — shorter than expected "
                  f"(~{expected_min_sec:.2f}s minimum heuristic). The output "
                  f"may be truncated. LISTEN to it before trusting it, "
                  f"especially if it contains critical content (names/numbers).")

        return wav, self._sample_rate

    def synthesize(
        self,
        text: str,
        language: str,
        speaker_wav: str,
        out_path: str = None,
        deterministic: bool = True,
    ) -> str:
        """
        text: reconstructed transcript text (may be multi-sentence)
        language: e.g. 'en' or 'hi' — must be in DEMO_LANGUAGES
        speaker_wav: short (6-10s), clean, mono, single-speaker reference clip
        deterministic: re-seeds RNG before generation so repeated calls with
                       the same inputs sound the same.
        """
        wav, sr = self.synthesize_array(text, language, speaker_wav, deterministic=deterministic)

        if out_path is None:
            # [FIX 16] Scratch files go under a dedicated tempdir, not the
            # working directory, so rehearsal runs don't litter the repo.
            out_path = os.path.join(_TMP_AUDIO_DIR, f"tts_out_{language}.wav")

        sf.write(out_path, wav, sr)
        return out_path

    # ------------------------------------------------------------------
    # [FIX 24] Code-switched (Hinglish) synthesis — STRETCH FEATURE, not
    # part of the core Day 1 task. See _split_by_language()'s docstring
    # above for the script-detection limitation before relying on this.
    # ------------------------------------------------------------------
    def synthesize_mixed(self, text: str, speaker_wav: str, out_path: str = None,
                          deterministic: bool = True) -> str:
        """
        Handles code-switched text by splitting into same-script runs
        (Devanagari -> 'hi', Latin -> 'en'), synthesizing each run with the
        matching language code but the SAME speaker latents (for voice
        consistency across the switch), then concatenating.

        UNTESTED beyond basic manual cases as of writing — validate with
        your actual rehearsed demo sentence before trusting this for a live
        run. Listen closely at each language-switch BOUNDARY specifically;
        that's where quality problems (abrupt tone/pace shift, odd pause)
        are most likely to show up, not mid-run.

        Any run in a language outside DEMO_LANGUAGES is skipped with a
        warning rather than raising, so one bad run doesn't kill an
        otherwise-mixed valid sentence. If this could silently drop
        USP-critical content (a number/name in a skipped run), that's a
        real risk — check the printed warning; don't assume "it ran" means
        "everything was said."
        """
        text = unicodedata.normalize("NFC", text)
        runs = _split_by_language(text)
        if not runs:
            raise ValueError("synthesize_mixed() received empty or whitespace-only text.")

        latents = self._get_conditioning_latents(speaker_wav)
        wav_segments = []

        with _INFERENCE_LOCK:
            for chunk_text, lang in runs:
                if lang not in DEMO_LANGUAGES:
                    print(f"[WARNING] Skipping run in unsupported language "
                          f"'{lang}': {chunk_text!r} — this content will be "
                          f"MISSING from the output audio.")
                    continue
                if deterministic:
                    _set_seed()
                wav_segments.append(self._infer_chunk_with_retry(chunk_text, lang, latents))

        if not wav_segments:
            raise ValueError(
                f"No synthesizable language runs found in text: {text!r} "
                f"(all runs were outside DEMO_LANGUAGES={DEMO_LANGUAGES})"
            )

        wav = np.concatenate(wav_segments) if len(wav_segments) > 1 else wav_segments[0]

        expected_min_sec = len(text) * _MIN_SEC_PER_CHAR
        actual_sec = len(wav) / self._sample_rate
        if actual_sec < expected_min_sec:
            print(f"[WARNING] Mixed-language output is {actual_sec:.2f}s for "
                  f"{len(text)} input characters — shorter than expected. "
                  f"LISTEN before trusting it.")

        if out_path is None:
            out_path = os.path.join(_TMP_AUDIO_DIR, "tts_out_mixed.wav")
        sf.write(out_path, wav, self._sample_rate)
        return out_path

    # ------------------------------------------------------------------
    # [FIX 28] Auto-routing convenience entry point
    # ------------------------------------------------------------------
    def synthesize_auto(self, text: str, speaker_wav: str, language_hint: str = "en",
                         out_path: str = None, deterministic: bool = True) -> str:
        """
        Routes to synthesize() or synthesize_mixed() based on whether the
        text actually contains mixed scripts, so callers (Backend Lead)
        don't need to detect code-switching themselves or know this
        distinction exists.

        This does NOT change the STT->TTS contract: input/output shapes are
        identical to synthesize()'s. It's an additional convenience method,
        not a replacement — synthesize() and synthesize_mixed() still exist
        and still work exactly as before for callers that want explicit
        control.

        language_hint: used only when the text is single-script AND that
        script is Latin (ambiguous between English and romanized Hindi) —
        defaults to 'en'. Devanagari-only text is always routed to 'hi'
        regardless of this hint.
        """
        has_devanagari = bool(_DEVANAGARI_RE.search(text))
        has_latin = bool(re.search(r"[a-zA-Z]", text))

        if has_devanagari and has_latin:
            return self.synthesize_mixed(text, speaker_wav, out_path=out_path,
                                          deterministic=deterministic)
        else:
            lang = "hi" if has_devanagari else language_hint
            return self.synthesize(text, lang, speaker_wav, out_path=out_path,
                                    deterministic=deterministic)

    # ------------------------------------------------------------------
    # Text-normalization check for USP-critical content
    # ------------------------------------------------------------------
    def compare_numeral_forms(self, digit_form: str, spelled_form: str, language: str,
                               speaker_wav: str) -> dict:
        """
        Synthesizes BOTH the raw-digit and spelled-out-numeral versions of
        the same sentence so you can A/B listen. Don't assume XTTS's
        internal text normalizer handles Hindi numerals the way you expect.
        """
        digit_out = self.synthesize(
            digit_form, language, speaker_wav,
            out_path=os.path.join(_TMP_AUDIO_DIR, f"numeral_check_digit_{language}.wav")
        )
        spelled_out = self.synthesize(
            spelled_form, language, speaker_wav,
            out_path=os.path.join(_TMP_AUDIO_DIR, f"numeral_check_spelled_{language}.wav")
        )
        return {
            "language": language,
            "digit_form_text": digit_form,
            "digit_form_audio": digit_out,
            "spelled_form_text": spelled_form,
            "spelled_form_audio": spelled_out,
            "action": "Listen to both. If they diverge audibly on the critical "
                      "word, standardize on whichever form STT/allocator actually "
                      "emits, and note the decision in contracts/interfaces.md.",
        }

    # ------------------------------------------------------------------
    # Pre-baked fallback for the exact demo sentence
    # ------------------------------------------------------------------
    def bake_demo_fallback(self, text: str, language: str, speaker_wav: str,
                            fallback_dir: str = "demo_fallback") -> str:
        """
        Generates and saves a known-good .wav for the literal rehearsed demo
        sentence — static safety net for CPML/network dependency + sampling
        variance. Kept in a real project folder (NOT temp) since it's an
        intentional deliverable asset. Re-run whenever the sentence changes.
        """
        os.makedirs(fallback_dir, exist_ok=True)
        safe_lang = language.replace("/", "_")
        out_path = os.path.join(fallback_dir, f"fallback_{safe_lang}.wav")
        self.synthesize(text, language, speaker_wav, out_path=out_path, deterministic=True)
        print(f"[TTS] Baked demo fallback -> {out_path}")
        return out_path

    # ------------------------------------------------------------------
    # Packet formatting
    # ------------------------------------------------------------------
    def to_packet_format(self, wav_path: str) -> dict:
        """
        Best-effort match to what the Backend Lead needs for base64-over-HTTP.
        [FIX 12] Includes "audio_format" since contracts/schemas.py's
        RunPipelineResponse-style shape likely needs it for AudioPlayer.jsx
        to build audio/${format}. VERIFY field names against the actual
        contracts/schemas.py — this is a documented guess, not a confirmed
        match.
        """
        audio, sr = librosa.load(wav_path, sr=None)
        with open(wav_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {
            "audio_base64": b64,
            "audio_format": "wav",
            "sample_rate": sr,
            "duration_sec": round(len(audio) / sr, 2),
        }

    def to_packet_format_from_memory(self, wav: np.ndarray, sr: int) -> dict:
        """
        In-memory variant — skips the disk round-trip. Use once this sits
        behind FastAPI as a per-request hot path. Pairs with
        synthesize_array(), which actually produces (wav, sr) in memory.
        """
        buf = io.BytesIO()
        sf.write(buf, wav, sr, format="WAV")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {
            "audio_base64": b64,
            "audio_format": "wav",
            "sample_rate": sr,
            "duration_sec": round(len(wav) / sr, 2),
        }

    def check_prosody(self, wav_path: str) -> dict:
        """
        Cheap sanity check only. Flags monotone/robotic output via pitch
        (F0) variance across the clip. Does NOT prove the cloned voice
        matches the reference speaker — that needs a human listening test.
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
            "flag_monotone": bool(len(f0_voiced) and np.nanstd(f0_voiced) < 5.0),
        }


if __name__ == "__main__":
    """
    Self-test — real sentences per language, including the critical-word
    sentence and a longer multi-clause sentence (exercises chunking +
    the [FIX 21]/[FIX 22]/[FIX 23] truncation-defense path).
    """
    wrapper = TTSWrapper()

    reference_clips = {
        "en": "reference_clips/speaker_en.wav",
        "hi": "reference_clips/speaker_hi.wav",
    }

    try:
        wrapper.preload_speakers(reference_clips)
    except FileNotFoundError as e:
        print(f"[SETUP] {e}")
        print("[SETUP] Record reference clips before running the rest of this test.")
        raise SystemExit(1)

    test_sentences = {
        "en": [
            "We need help at grid reference two eight point five north.",
            "The weather is good today.",
        ],
        "hi": [
            "हमें मदद चाहिए।",
            "आज मौसम अच्छा है।",
            # Longer, multi-sentence Hindi input — this is the exact shape
            # of sentence that cut off before [FIX 21]/[FIX 22]/[FIX 23].
            "यह टीम अल्फा बोल रही है। हमें ग्रिड संदर्भ दो आठ दशमलव पांच उत्तर पर तुरंत मदद चाहिए।",
        ],
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
            results.append({"lang": lang, "text": sentence, "status": status,
                             "prosody": prosody})

    print(json.dumps(results, indent=2, ensure_ascii=False))

    # [FIX 24] Hinglish/code-switched test — STRETCH FEATURE. If this fails
    # or sounds bad at the language-switch boundary, that's expected/known
    # risk (see synthesize_mixed()'s docstring) — not a sign of a fresh bug.
    try:
        mixed_out = wrapper.synthesize_mixed(
            "Team Alpha यहाँ है। We need मदद at grid reference two eight point five.",
            speaker_wav=reference_clips["en"],
        )
        print(f"[TTS] Hinglish test output: {mixed_out} — LISTEN to the "
              f"language-switch boundaries specifically before trusting this.")
    except Exception as e:
        print(f"[WARN] Hinglish synthesis failed: {e}")

    # [FIX 28] Auto-routing test — should transparently choose the right
    # path for a plain-English sentence, a plain-Hindi sentence, and a
    # mixed sentence, without the caller specifying which.
    try:
        auto_en = wrapper.synthesize_auto(
            "We need help at grid reference two eight point five north.",
            speaker_wav=reference_clips["en"],
        )
        auto_hi = wrapper.synthesize_auto(
            "हमें मदद चाहिए।",
            speaker_wav=reference_clips["hi"],
        )
        auto_mixed = wrapper.synthesize_auto(
            "Team Alpha यहाँ है। We need मदद at grid reference two eight point five.",
            speaker_wav=reference_clips["en"],
        )
        print(f"[TTS] synthesize_auto results -> en: {auto_en}, hi: {auto_hi}, "
              f"mixed: {auto_mixed}")
    except Exception as e:
        print(f"[WARN] synthesize_auto test failed: {e}")

    try:
        numeral_check = wrapper.compare_numeral_forms(
            digit_form="Coordinates two eight point five north, seven seven point one east.",
            spelled_form="Coordinates twenty-eight point five north, seventy-seven point one east.",
            language="en",
            speaker_wav=reference_clips["en"],
        )
        print(json.dumps(numeral_check, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[WARN] Numeral-form check failed: {e}")

    try:
        wrapper.bake_demo_fallback(
            text="We need help at grid reference two eight point five north.",
            language="en",
            speaker_wav=reference_clips["en"],
        )
    except Exception as e:
        print(f"[WARN] Could not bake demo fallback: {e}")