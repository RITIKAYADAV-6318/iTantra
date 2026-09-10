# iTantra — Final 4-Day Build Plan (Full Scope, 6-Person Team)
**SIH26173 | ISRO | Neural Transceiver for Low-Bitrate Radio Links**

*This is the current, active plan — compressed from 6 days to 4, with full scope
retained (including QIEA/QPSO and sound-event tags) because the team is committing
full days across 6 people. Nothing is cut in advance; instead, end-of-day checkpoints
tell you honestly whether something needs to be deprioritized, based on real progress
— not a guess made today.*

---

## Proposed Solution (150 words)

iTantra enables clear voice communication over extremely low-bitrate, noisy radio links by converting speech to text at the sender, transmitting compact data, and reconstructing natural speech at the receiver. A multilingual Speech-to-Text engine, fine-tuned on Indian languages, transcribes speech, while compact speaker-embedding and prosody vectors preserve the speaker's voice and tone. The core innovation is a criticality- and confidence-aware adaptive bit allocator, powered by a quantum-inspired optimization algorithm, which prioritizes bandwidth for words that are both uncertain and semantically critical — numbers, names, coordinates — while compressing filler words harder, directly preventing "confidently wrong" transmissions. A lightweight sound-event tag preserves non-verbal cues like sirens or distress signals. Text-to-Speech reconstructs natural, speaker-consistent audio at the receiver. Built entirely in software with a simulated channel, the system runs offline on edge hardware, making it ideal for defense, disaster-response, and remote or space communication scenarios where connectivity is minimal but clarity and accuracy are critical.

---

## Final Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Language (backend) | Python | STT, TTS, allocator, channel sim |
| STT (ASR) | **faster-whisper, `"small"` model** (pretrained, CPU-friendly) — *IndicConformer was the original plan but requires NVIDIA NeMo/Linux setup; swapped Day 1. "small" chosen over "medium" for speed given the time constraint — verify against your actual rehearsed demo sentence before locking in (see contracts/interfaces.md change log). Same `transcribe()` contract either way, swap is one env var or one file if revisited.* | Speech → text + per-token confidence |
| TTS | **Coqui TTS (`xtts_v2`)** (pretrained, voice-cloning from a short reference clip) — *AI4Bharat Indic-TTS was the original plan but has its own custom setup (repo clone, manual checkpoint pulls); swapped Day 1 for the same install-risk reasons as STT. Verify your two demo languages work cleanly on your actual install before relying on it — Coqui's multilingual support has shifted across versions.* | Text + speaker/prosody → natural speech |
| Speaker embedding | SpeechBrain or Resemblyzer | Preserve speaker identity |
| Signal processing | librosa | Pitch/energy extraction for prosody |
| Criticality tagging | Plain Python + `re` | Flags numbers, coordinates, names, negations |
| Bit allocator | Custom Python — greedy (must-have) + QIEA/QPSO (attempted in parallel, not sequential) | **Core USP** |
| Channel simulator | Custom Python | Simulates bad bitrate/noise |
| Sound-event tags | Custom Python, simple pattern/energy detection | Side-channel for non-verbal cues |
| Packet format | Pydantic model (`contracts/schemas.py`) | Enforced schema shared across modules |
| Backend API bridge | FastAPI | Exposes pipeline to UI over HTTP, serves audio as base64 |
| Frontend/Dashboard | React (Vite) + recharts | Sliders, toggle, protection chart, before/after audio players |
| Fallback dashboard | Streamlit | Backup only, in `ui/streamlit_fallback/` |
| Contracts | `contracts/interfaces.md` + `contracts/schemas.py` | Frozen module boundaries |
| Version control | Git + GitHub | — |

**Not in scope regardless of timeline** (roadmap/slide claims only): ONNX Runtime, GNU Radio/SDR hardware, Raspberry Pi/Jetson, torchaudio, gRPC, BPE+entropy coding, FEC, post-quantum signatures. These were never buildable in any version of this plan without dedicated hardware and days this project doesn't have — they were cut for capability reasons, not time reasons, so the 4-day compression doesn't change this list.

---

## The Rule That Makes "Build Everything" Survivable

**Nothing new starts after Day 3 evening's checkpoint. Day 4 is fix-and-rehearse only.**
This is not a scope cut — it's an honest cutoff point. You're not deciding today what
to skip; you're giving yourselves a moment on Day 3 evening to look at real results and
decide, with actual information, what needs to be simplified for the live demo versus
what's solid enough to show as-is.

---

## Contracts-First Workflow (first 30 minutes of Day 1 — before any code)

1. Whole team reads `contracts/interfaces.md` together.
2. Lock every field: STT→Allocator, Allocator→Packet, Packet→Channel→TTS, Backend→UI.
   Add anything missing now.
3. Agree: any contract change gets posted to the team + logged in `interfaces.md`'s
   change log + updated in `contracts/schemas.py`, all in the same commit.
4. After this, everyone builds independently against the frozen contract — this is
   what lets 6 people work in parallel without breaking each other's code.
5. Run `tests/test_contracts.py` after touching any module boundary, and always
   before merging into `main`.

---

## Team Roles

| Role | Owns |
|---|---|
| STT Lead | Pretrained STT, LID, per-token confidence — validated against `SttOutput` contract |
| TTS Lead | Pretrained TTS, speaker embedding + prosody conditioning |
| Allocator Lead (+ 1 helper on Day 2) | Criticality tagger, greedy allocator, QIEA/QPSO benchmarking — validated against `AllocatorOutput` contract |
| Channel/Systems Lead | Channel simulator, protection-aware degradation, sound-event tags |
| Integration/Backend Lead | FastAPI bridge, wires all modules, base64 audio encoding |
| React/UI Lead | Dashboard: sliders, toggle, protection chart, before/after audio players |
| Everyone | Pitch deck, testing, rehearsal on Day 4 — this is a whole-team effort, not one role's job |

With 6 people, one person doubles up (e.g., Allocator Lead also drives QIEA once
greedy works, or Channel Lead also builds sound-events after the simulator is done).

---

## Day-by-Day Plan

### Day 1 — Contracts + Four Parallel Tracks
**Goal by end of day:** every module works standalone against the frozen contract,
even if the data flowing between them is still mocked.

- **First 30 min, whole team:** contracts kickoff (see above).
- **STT Lead:** wrap pretrained faster-whisper (`"small"` model — see decision log in
  `contracts/interfaces.md`), confirm per-token confidence is real and accessible,
  test on both demo languages with 5-10 sentences each. **Explicitly test your actual
  rehearsed demo sentence** (the one with a number/name/coordinate) — confirm `"small"`
  transcribes it correctly. This step isn't optional: since `"medium"` isn't being
  used as a fallback, audio recording quality (quiet room, closer mic, clear
  enunciation) is now your main lever if the critical word comes out wrong — fix that
  before assuming the model is the problem.
- **TTS Lead:** wrap pretrained Coqui TTS (`xtts_v2` — see decision log in
  `contracts/interfaces.md`), get voice-cloning conditioning working (pass a short
  reference clip of the speaker as `speaker_embedding`), and confirm basic prosody.
  **Explicitly test both demo languages** the same way STT was tested — Coqui's
  multilingual language coverage has shifted across versions, don't assume it
  handles your languages cleanly without checking.
- **Allocator Lead:** build the criticality tagger. This doesn't depend on STT/TTS —
  build and test it against mock text today.
- **Channel/Backend Lead:** build the channel simulator skeleton and the FastAPI
  scaffold (`ui/backend/api.py`) — both testable against mock data before real
  modules exist.
- **React Lead:** start the dashboard against the mock API responses already in the
  repo (`ui/backend/api.py`'s stubs return valid mock JSON) — no need to wait on
  anyone else to start building sliders, toggle, chart, and audio player UI.
- **Evening:** everyone demos their module running standalone, live.

### Day 2 — Real Allocator + QIEA in Parallel + Real Models
**Goal by end of day:** greedy allocator works on real text with real confidence
scores; QIEA is underway alongside it, not after it.

- **Allocator Lead + 1 helper:** build the greedy allocator for real, validate against
  `AllocatorOutput` contract. Test the "grid reference 4729"-style sentence — confirm
  the number gets protected while filler doesn't. Once greedy works, the helper starts
  QIEA/QPSO on the same objective function so it's not purely sequential.
- **STT/TTS Leads:** finish real model integration on both languages; fine-tune only
  if there's slack time.
- **Channel/Backend Lead:** finish the channel simulator with protection-aware
  degradation (high-protection tokens survive noise better than low-protection ones —
  this is the mechanism that proves the USP live).
- **React Lead:** continues building against mocks — audio players, sliders, chart,
  all functional with fake data by tonight.
- **Checkpoint (end of day, whole team, 10 min):** Does the greedy allocator work on
  the test sentence? If yes, QIEA continues tomorrow as planned. If no, pull whoever's
  ahead (likely React, since it works against mocks) to help the allocator team first
  thing tomorrow morning — QIEA gets deprioritized for a few hours, not cut.

### Day 3 — Full Integration + Sound-Events + QIEA Benchmark
**Goal by end of day:** the whole pipeline runs end-to-end, live, on one laptop, with
real audio in and real audio out.

- **Backend Lead:** wires everything real — STT → allocator → channel → TTS behind
  `/run_pipeline`, base64-encodes output audio for the frontend.
- **Channel Lead** (once the simulator is solid): builds sound-event tagging
  ([siren], [gunfire]) as a side-channel addition on top of the existing packet
  schema — genuinely cheap once the packet format already exists.
- **Allocator team:** benchmarks QIEA against greedy — a real quality-vs-bitrate
  curve, not a claim. If the improvement isn't real and measurable, that's the honest
  result — present greedy as the working system and QIEA as "designed, benchmarked,
  here's what we found" rather than forcing a number that isn't there.
- **React Lead:** swaps every mocked API call for the real backend, now that it's live.
- **Checkpoint (end of day, whole team, mandatory):** run `tests/test_contracts.py`,
  then run the full demo once, live, exactly as you'll present it. Anything broken
  here is the first thing fixed tomorrow morning — **no new features start until this
  checkpoint run is clean.**

### Day 4 — Fix, Test, Pitch, Rehearse
**Goal by end of day:** a demo that's been run enough times that nothing about it
surprises you on stage.

- **Morning:** fix whatever broke in yesterday's checkpoint run. This is priority zero
  — nothing else starts until the end-to-end demo runs clean.
- **Midday:** WER numbers on both languages using the locked `"small"` faster-whisper
  model, finalize the QIEA-vs-greedy benchmark chart, run a quick informal listening
  test with 2-3 people outside the team, record a full backup video of the exact demo
  sequence. UI theme (dark HUD style, already built — see
  `docs/SCREEN_ARCHITECTURE.md`) gets wired to real data now that the backend is live;
  if it's already fully wired from earlier days, this is just a final pass, not new
  work.
- **Afternoon:** build the pitch deck — solution summary, USP line, live demo
  walkthrough, bandwidth-savings number, WER table, QIEA benchmark chart, roadmap
  slide for anything genuinely unfinished.
- **Evening — protected no matter what:** rehearse the full live demo at least 5
  times back to back, including the audio-playback moment and the bitrate-slider
  moment. If something is still rough, simplify it for the demo rather than skipping
  rehearsal to keep polishing it. Rehearse answers to the known objections:
  confidently-wrong outputs, real-time claims, novelty, quantum-inspired skepticism.

---

## UI Theme — Dark HUD Style, Clarity First

The dashboard uses a dark, glowing-blue "command center" aesthetic — it matches the
ISRO/defense-comms framing of the pitch. **Clarity is the non-negotiable priority over
the theme**: every visual element must map to a real, live value from the pipeline; if
it's decorative and doesn't serve legibility, it doesn't get built. See
`docs/SCREEN_ARCHITECTURE.md` for the full wireframe, panel-by-panel feature map, and
the "Node" concept that answers how sender/receiver screens work — both for the
one-laptop demo and for scaling to real multi-device deployment later.

Already built in the repo: `ui/frontend/src/theme.js` (shared colors/fonts/panel
styles), `RadialGauge.jsx` (live bitrate readout, styled like the reference HUD but
showing real data instead of decoration), and matching restyles of `ModeToggle.jsx`,
`BitrateSlider.jsx`, `AudioPlayer.jsx`, `ProtectionChart.jsx`, and `App.jsx`.

---

## What to Emphasize Throughout (check every evening)

- [ ] Does `python tests/test_contracts.py` still pass?
- [ ] Does the demo run end-to-end right now, live, on this laptop?
- [ ] Does the allocator visibly protect a number/name under a bad channel?
- [ ] **Does `"small"` faster-whisper correctly transcribe your rehearsed demo
      sentence, especially the critical word (number/name/coordinate)?** If not, fix
      the recording environment before rehearsal, not the model.
- [ ] Do the before/after audio players actually play something audibly different?
- [ ] Does reconstructed speech still sound like the speaker, not robotic?
- [ ] Have you avoided claiming real-time duplex conversation anywhere?
- [ ] Is every claim backed by a number, or clearly labeled as roadmap?
- [ ] (Day 3+) Did today's checkpoint run pass before anyone started new work?

## One-Line Pitch (memorize this)

*"We don't just protect the connection — we protect the words that matter most."*
