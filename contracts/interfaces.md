# interfaces.md — Module Communication Contracts

**Rule: freeze what crosses a module boundary. Internal implementation is 100% up to
the person building it.** If you need to change anything in this file, say so in the
team channel and update `contracts/schemas.py` in the same commit — nobody should
discover a contract change because their code broke.

This file is the plain-English version. `contracts/schemas.py` is the enforced version
(actual Python types) — import from there, don't just read this and hand-roll dicts.

---

## 1. STT → Allocator

**What STT produces, per utterance:**

| Field | Type | Meaning |
|---|---|---|
| `language` | `str` | detected language code, e.g. `"hi"`, `"en"` |
| `text` | `str` | transcribed sentence |
| `tokens` | `list[str]` | tokenized form of `text`; used to align confidence values |
| `confidence_per_token` | `list[float]` | one score `[0,1]` per token, **same length as `tokens`** |

> **Note (Day 2):** call `get_stt_output()` for pipeline integration — it returns
> the full per-token `SttOutput` contract. `transcribe()` is a simpler helper that
> now returns an averaged confidence float (not a per-token list) and must not be
> used to feed the allocator.

**Allocator input boundary:**

```text
allocate(
    text,
    confidence_per_token,
    channel_bitrate_kbps,
    language
)
```

The allocator receives the full text, the corresponding confidence_per_token,
the current channel bitrate, and the detected language.

language is required and must be "en" or "hi". The allocator must not silently
assume English if the language is missing.

The allocator internally runs the criticality tagger to generate
criticality_per_token. The tagger is an internal allocator component, not a
separate frozen module boundary.

The allocator tokenizes text internally and verifies that the resulting tokens
remain aligned with the STT confidence values.

STT audio, timestamps, and other internal STT details do not cross this boundary.



## 2. Allocator → Packet / Channel

**What the allocator produces:**

| Field | Type | Meaning |
|---|---|---|
| `tokens` | `list[str]` | tokenized from the STT `text`; must remain aligned with `confidence_per_token` |
| `confidence_per_token` | `list[float]` | passed through unchanged from STT |
| `criticality_per_token` | `list[float]` | `[0,1]` per token, from the criticality tagger |
| `protection_per_token` | `list[float]` | `[0,1]` per token — how much bandwidth/redundancy this token got. **This is the field the whole USP hinges on — it must always be present and the same length as `tokens`.** |
| `allocated_for_bitrate_kbps` | `float` | bitrate the allocator assumed while calculating token protection |
| `language` | `str` | language passed through from STT, e.g. `"hi"`, `"en"` |
| `speaker_embedding` | `object \| None` | optional, from TTS module's extractor |
| `prosody_vector` | `object \| None` | optional |
| `sound_event_tags` | `list[str]` | optional list of detected environmental sound events, e.g. `["siren", "gunfire"]` |
This is exactly the `Packet` dataclass in `channel/packet.py` — the allocator returns
this shared `Packet`, not a raw dict.

---

## 3. Packet → Channel Simulator → TTS

**Channel simulator contract:**
- Input: a `Packet` + `bitrate_kbps: float` + `noise_level: float` (0=clean, 1=very noisy)

- `bitrate_kbps` is the **current channel bitrate**. It may differ from
  `packet.allocated_for_bitrate_kbps`, which records the bitrate the allocator
  assumed when calculating protection.

- Output: a `Packet` — same shape, but token fields may be degraded/corrupted based on
  `noise_level` and each token's `protection_per_token` value. The current simulator
  uses protection-aware corruption: higher-protection tokens have a lower probability
  of corruption at the same noise level.
- Separately, `send_raw_audio(audio, bitrate_kbps, noise_level) -> audio` exists only
  for the "before" baseline demo — it does not go through the Packet format at all.

**TTS contract (receiver side):**
- `tts/tts.py` exposes a class, not a bare function:
```python
  class TTSWrapper:
      def synthesize(self, text: str, language: str, speaker_wav: str,
                      out_path: str = None, deterministic: bool = True) -> str:
          """
          language: 'en' or 'hi' — matches the language field from SttOutput.
          speaker_wav: path to a 6-10s clean mono reference clip. XTTS computes
                       the speaker embedding internally from this clip; no
                       separate speaker_embedding/prosody_vector input exists.
          Returns: path to the synthesized .wav file.
          """

      def to_packet_format(self, wav_path: str) -> dict:
          """Returns {"audio_base64": str, "audio_format": "wav",
          "sample_rate": int, "duration_sec": float} for the Backend bridge."""
```
- Callers: `TTSWrapper().synthesize(...)` then `.to_packet_format(...)` —
  not a bare `synthesize()` function.
---

## 4. Backend (FastAPI) → UI (React)

**What every UI feature receives, per pipeline run** (`POST /run_pipeline` response):

| Field | Type | Which UI feature uses it |
|---|---|---|
| `language` | `str` | language display |
| `text` | `str` | transcribed text display |
| `confidence_per_token` | `list[float]` | protection chart, confidence highlighting |
| `criticality_per_token` | `list[float]` | protection chart |
| `protection_per_token` | `list[float]` | protection chart (this is the bar height) |
| `raw_audio_bytes` | `int` | bandwidth-savings stat (baseline mode) |
| `packet_bytes` | `int` | bandwidth-savings stat (iTantra mode) |
| `mode` | `str` | `"baseline"` or `"itantra"` — drives before/after audio player |
| `audio_base64` | `str \| None` | audio playback component |
| `audio_format` | `str` | audio playback component (decode hint, e.g. `"wav"`) |

**If the UI needs a new field (e.g. latency, packet loss %, packets sent/lost)**, add it
to `RunResponse` in `ui/backend/api.py` **and** to this table in the same commit — same
rule as everywhere else in this file.

---

## Change log

Record every contract change here so anyone can scroll and see what shifted, when, and
who to ask about it.

| Date | Field/Contract changed | Changed by | Reason |
|---|---|---|---|
| Day 1 | Initial contracts frozen | — | Team kickoff |
| Day 1 | STT implementation: IndicConformer → faster-whisper (contract unchanged) | STT Lead | IndicConformer needs NeMo/Linux setup — too much install risk for Day 1. `transcribe()` signature identical either way. |
| Day 1 | STT model size locked to "small" (not "medium") | STT Lead | Time constraint — "small" is faster and lower-risk. Verified against rehearsed demo sentence before locking in (see docs/STATUS.md). If a critical word (number/name/coordinate) is ever mistranscribed, fix audio quality first (quiet room, closer mic) before considering "medium". |
| Day 1 | TTS implementation: AI4Bharat Indic-TTS → Coqui TTS (xtts_v2) (synthesize() contract unchanged) | TTS Lead | Applying the same install-risk check already done for STT. Indic-TTS needs a custom repo setup with manual checkpoint pulls; Coqui TTS is a plain `pip install`. Must verify both demo languages work cleanly on the team's actual install before relying on it live. |
| Day 1 | Channel contract: allocator bitrate renamed to `allocated_for_bitrate_kbps`; `language` added to Packet; channel `send()` now takes/returns `Packet` with current `bitrate_kbps` passed separately | Channel/Systems Lead | Removes ambiguity between allocator bitrate assumptions and current channel bitrate, and makes the Packet/Channel boundary consistent |
| Day 2 | Allocator contract: `language` made a required input; criticality tagging moved inside the allocator | Allocator/Channel Lead | Supports the bilingual `"en"` / `"hi"` pipeline and keeps the tagger as an internal allocator component rather than a separate pipeline boundary |
| Day 2 | Channel degradation: `send()` now uses `protection_per_token` when determining token corruption | Channel/Systems Lead | Implements protection-aware degradation so highly protected tokens are more resilient to channel noise |
| Day 2 | STT: `transcribe()` now returns averaged confidence (float) instead of per-token list; use `get_stt_output()` for pipeline integration instead | STT Lead | `transcribe()` was simplified for standalone CLI use; `get_stt_output()` remains contract-compliant |
| Day 2 | TTS contract: replaced planned `synthesize(text, speaker_embedding, prosody_vector)` with `TTSWrapper.synthesize(text, language, speaker_wav, out_path, deterministic)` | TTS Lead | XTTS v2 computes the speaker embedding internally from a reference clip — no separate embedding/prosody_vector exists to pass in. Backend must call the class method + `to_packet_format()`, not a bare function. |
| Day 3 | Sound-event metadata: `sound_event_tag` changed to `sound_event_tags` (`list[str]`) | Channel/Systems Lead | Supports simultaneous environmental sound events in mixed audio while keeping event metadata separate from speech text |