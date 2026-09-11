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
| `tokens` | `list[str]` | `text` split into words — allocator/criticality operate on this, not raw `text` |
| `confidence_per_token` | `list[float]` | one score `[0,1]` per token, **same length as `tokens`** |

Allocator consumes exactly these four fields. It does not need audio, timestamps, or
anything else from STT.

---

## 2. Allocator → Packet / Channel

**What the allocator produces:**

| Field | Type | Meaning |
|---|---|---|
| `tokens` | `list[str]` | passed through unchanged from STT |
| `confidence_per_token` | `list[float]` | passed through unchanged from STT |
| `criticality_per_token` | `list[float]` | `[0,1]` per token, from the criticality tagger |
| `protection_per_token` | `list[float]` | `[0,1]` per token — how much bandwidth/redundancy this token got. **This is the field the whole USP hinges on — it must always be present and the same length as `tokens`.** |
| `allocated_for_bitrate_kbps` | `float` | bitrate the allocator assumed while calculating token protection |
| `language` | `str` | language passed through from STT, e.g. `"hi"`, `"en"` |
| `speaker_embedding` | `object \| None` | optional, from TTS module's extractor |
| `prosody_vector` | `object \| None` | optional |
| `sound_event_tag` | `str \| None` | optional, e.g. `"[siren]"` |

This is exactly the `Packet` dataclass in `channel/packet.py` — the allocator should
return one of these, not a raw dict.

---

## 3. Packet → Channel Simulator → TTS

**Channel simulator contract:**
- Input: a `Packet` + `bitrate_kbps: float` + `noise_level: float` (0=clean, 1=very noisy)

- `bitrate_kbps` is the **current channel bitrate**. It may differ from
  `packet.allocated_for_bitrate_kbps`, which records the bitrate the allocator
  assumed when calculating protection.

- Output: a `Packet` — same shape, but some fields may be degraded/corrupted based on
  `noise_level` and each token's `protection_per_token` value. **Day 1 uses a basic
  corruption model; protection-aware degradation will be added later.**
- Separately, `send_raw_audio(audio, bitrate_kbps, noise_level) -> audio` exists only
  for the "before" baseline demo — it does not go through the Packet format at all.

**TTS contract (receiver side):**
- Input: `text: str`, `speaker_embedding: object | None`, `prosody_vector: object | None`
- Output: `audio` — raw bytes (WAV), owner of `tts/` decides internal format but must
  document it here once fixed (currently: WAV bytes).

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