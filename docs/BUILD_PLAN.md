# iTantra — 6-Day Build Plan
**SIH26173 | ISRO | Neural Transceiver for Low-Bitrate Radio Links**

---

## Proposed Solution (150 words)

iTantra enables clear voice communication over extremely low-bitrate, noisy radio links by converting speech to text at the sender, transmitting compact data, and reconstructing natural speech at the receiver. A multilingual Speech-to-Text engine, fine-tuned on Indian languages, transcribes speech, while compact speaker-embedding and prosody vectors preserve the speaker's voice and tone. The core innovation is a criticality- and confidence-aware adaptive bit allocator, powered by a quantum-inspired optimization algorithm, which prioritizes bandwidth for words that are both uncertain and semantically critical — numbers, names, coordinates — while compressing filler words harder, directly preventing "confidently wrong" transmissions. A lightweight sound-event tag preserves non-verbal cues like sirens or distress signals. Text-to-Speech reconstructs natural, speaker-consistent audio at the receiver. Built entirely in software with a simulated channel, the system runs offline on edge hardware, making it ideal for defense, disaster-response, and remote or space communication scenarios where connectivity is minimal but clarity and accuracy are critical.

---

## Non-Negotiables — Read Before Day 1

You submitted a specific USP: **criticality- and confidence-aware adaptive allocation**. That claim is now the thing judges will test you on. The single biggest risk to this project is spending 6 days polishing STT/TTS quality and never actually building the allocator — leaving your registered USP unproven on stage. Everything below is sequenced to protect that.

1. **The allocator (with confidence + criticality inputs) is the product.** STT and TTS are necessary plumbing, not the differentiator. Don't over-invest in them once they "work."
2. **Working > perfect, every day.** At the end of each day you must have something that *runs end-to-end*, even if crude. Never leave the pipeline broken overnight.
3. **Scope to 2 languages only** (e.g., Hindi + English, or Hindi + one more you verify is strong). Everything else — Odia/Assamese/code-switching/sound-events — is a slide claim or a stub, not a live demo dependency.
4. **Greedy allocator is your real fallback.** Build it on Day 3 no matter what. The quantum-inspired (QIEA/QPSO) version is layered on top only if time allows — if it isn't benchmarked and working by Day 5 evening, present it as "designed, partially benchmarked" rather than faking it live.
5. **One laptop, software-only demo.** No hardware, no SDR, no second device. Two terminal windows / two browser tabs, one machine.
6. **Never claim real-time conversation.** Frame it explicitly as "near-real-time, sentence-level voice relay" — like a walkie-talkie "over" pause. This is a pitch-language fix, not engineering work — but say it out loud in rehearsal so no one on the team accidentally overclaims on stage.

---

## Team Roles (assign before Day 1 starts)

| Role | Owns |
|---|---|
| STT lead | Pretrained model, fine-tuning if time allows, confidence score extraction, LID |
| TTS lead | Pretrained model, speaker embedding + prosody conditioning |
| Allocator/Systems lead | Criticality tagger, greedy allocator, QIEA/QPSO, channel simulator |
| Integration/UI lead | Pipeline wiring, dashboard, demo toggle, bitrate slider |
| Pitch/Docs lead | Slides, WER/benchmark numbers, demo script, backup video, rehearsal |

If you're fewer than 5 people, merge Allocator+Integration or STT+TTS — do **not** drop the Pitch/Docs role; a strong demo with a weak pitch loses to a weaker demo with a sharp pitch.

---

## Day-by-Day Plan

### Day 1 — Foundation: STT + TTS Working Alone
**Goal by end of day:** You can speak a sentence and hear it come back out, no compression, no channel, no allocator — just STT → TTS, in one language.

- Set up repo structure: `stt/`, `tts/`, `channel/`, `allocator/`, `ui/`, `docs/`.
- Pull a pretrained multilingual STT model (Whisper or AI4Bharat IndicConformer) — **do not train from scratch.**
- Pull a pretrained TTS model (Coqui TTS / AI4Bharat Indic-TTS) — **do not train from scratch.**
- Wrap STT as `audio -> text` and TTS as `text -> audio`, each as a plain Python function.
- Confirm both work on your 2 chosen demo languages with 5-10 test sentences each, including at least one sentence with a number, name, and coordinate-style string (you'll need these later).
- **Emphasize:** confirm the confidence score is accessible from your STT output *today* — you need this working, not just theoretically available, because Day 3 depends on it.

**Cut if behind:** Drop the second language to a stub for now; get one language rock-solid first.

---

### Day 2 — Speaker Identity, Prosody, and the Compression Packet
**Goal by end of day:** Reconstructed speech sounds like the actual speaker, and you have a defined, small "packet" format.

- Extract a speaker embedding (x-vector) once per session — not per sentence.
- Extract pitch/energy (librosa) per sentence; keep it small (a handful of numbers, not raw signal).
- Condition TTS output on speaker embedding + prosody so the voice is recognizable, not robotic.
- Define your packet schema now, on paper: `{text_tokens, speaker_id, prosody_vector, criticality_flags, confidence_flags}`. This schema is what the allocator will act on tomorrow — get the fields agreed today so nobody's building against a moving target.
- Measure packet size vs. raw audio size and log the number — this is a concrete demo statistic judges respond to.

**Emphasize:** "sounds like the person, not a robot" is one of your registered USP bullets — don't skip prosody conditioning to save time; it's cheap relative to its payoff.

**Cut if behind:** Skip BPE/entropy coding sophistication — plain text is already tiny; don't burn a day compressing something that's already small.

---

### Day 3 — The Allocator: Criticality + Confidence (Your Core USP)
**Goal by end of day:** A working greedy allocator that reads confidence + criticality per word and visibly protects the "important + unsure" words when bandwidth drops.

- Build a lightweight criticality tagger: regex/dictionary pass is enough — flag numbers, names, coordinates, negations ("not", "no"), callsigns. Do not overbuild this with a full NER model.
- Confirm per-token confidence is flowing from STT (built Day 1).
- Build the **greedy baseline allocator first**: given a bitrate budget, protect high-criticality + low-confidence words first (extra FEC bits or a phonetic/raw-audio fallback for that word), compress everything else harder as bandwidth drops.
- Test with your prepared "grid reference 4729" -style sentence: confirm that under a tight bitrate, the number survives clean while filler words degrade first.
- **This is the single most important checkpoint in the whole 6 days.** If this isn't working by Day 3 evening, everything else is secondary — reallocate people here on Day 4 morning if needed.

**Only if Day 3 finishes early:** Start the QIEA/QPSO version on top of the same objective function (confidence + criticality + channel state). Benchmark it against greedy on a quality-vs-bitrate curve. If you don't get a clean, real improvement number, don't claim one — present greedy as "working system," QIEA as "designed, in progress" on a slide with pseudocode.

---

### Day 4 — Channel Simulator + Full Pipeline Integration
**Goal by end of day:** One continuous pipeline: mic in → STT → allocator → simulated bad channel → TTS → speaker out, running as two processes (Sender/Receiver) on one laptop.

- Build the channel simulator: throttle bitrate (e.g., configurable 1-5 kbps), add noise/packet loss. Software only — no GNU Radio hardware dependency needed for the demo.
- Confirm raw audio through this channel visibly breaks down (this is your "before" demo — you need it to fail convincingly and consistently).
- Confirm your compressed, allocator-protected packet survives the same channel (your "after" demo).
- Wire Sender and Receiver as two separate processes/windows, connected only through the simulator — not a real network hop.
- **Emphasize:** rehearse the failure case as much as the success case. A "before" demo that doesn't clearly fail undercuts your entire pitch.

**Cut if behind:** Skip FEC/Reed-Solomon sophistication — a simple "drop/corrupt X% of low-priority bits" simulation is enough to sell the story.

---

### Day 5 — Dashboard, Sound-Event Tags, Polish, Edge Case Pass
**Goal by end of day:** A live dashboard judges can watch, the sound-event side-channel working, and the system tested against realistic failure modes.

- Build a simple Streamlit or React dashboard: detected language, live bitrate meter, packet size vs. raw size, a toggle for "normal call" vs. "iTantra mode," and a draggable bitrate slider.
- Add the lightweight sound-event tag ([siren], [gunfire], [distress-tone]) — cheap, few-bytes side-channel, high narrative payoff for the defense/disaster framing. Don't build full sound-event detection from scratch; a simple energy/pattern-based classifier on a few pre-recorded clips is enough for a hackathon demo.
- Run through edge cases deliberately: silence, overlapping speech, very degraded input — fix the 2-3 worst failures you find, don't chase every bug.
- Record a full backup video of the exact demo sequence working, in case live audio fails on stage.
- **Emphasize:** the bitrate-slider "wow" moment (drag it down live, watch words survive while filler degrades) is your best single beat — protect the time to rehearse it, don't let dashboard polish eat into rehearsal time.

**Cut if behind:** Sound-event tags become a slide claim with one pre-recorded example instead of a live feature.

---

### Day 6 — Testing, Benchmarks, Pitch, Rehearsal
**Goal by end of day:** Numbers ready, story tight, demo rehearsed until boring.

- Run WER on your 2 demo languages and record the numbers — use as a slide, not a live risk.
- If you have a QIEA benchmark, put the quality-vs-bitrate curve on a slide. If not, put the greedy-vs-nothing comparison instead — still a real number.
- Get a few people outside the team to blind-listen to reconstructed vs. original speech; note their reaction as an informal quality claim.
- Build the pitch deck: solution summary, USP line, live demo, bandwidth-savings number (e.g., "X kbps down to under 1 kbps"), one simple diagram of the allocator (no deep math on stage), roadmap slide for under-represented languages and code-switching (explicitly framed as future work, not live-demoed).
- **Rehearse the demo end-to-end at least 5 times**, including deliberately triggering the "before" failure and the bitrate-slider moment. Time it — target under 3 minutes for the live segment.
- Prepare answers, out loud, as a team, for the questions you already know are coming:
  - *"Doesn't ASR error just become a confidently-wrong TTS output?"* → explain confidence+criticality flagging as your direct answer.
  - *"Is this real-time?"* → "near-real-time, sentence-level relay," walkie-talkie framing.
  - *"Is this a novel idea?"* → own it: STT-TTS relay is established research; your differentiator is Indian-language coverage, prosody preservation, and the criticality-aware allocator.
  - *"Why quantum-inspired, why not just a heuristic?"* → have the benchmark ready, or the honest "in progress, here's the theory" fallback.

---

## What to Emphasize Throughout (checklist to re-check every evening)

- [ ] Does the demo still run end-to-end right now, live, on this laptop?
- [ ] Does the criticality+confidence allocator visibly protect a number/name under a bad channel? (This is the one thing you cannot cut.)
- [ ] Does reconstructed speech still sound like the speaker, not robotic?
- [ ] Is the "before" (raw audio) failure still clearly, audibly broken?
- [ ] Have you avoided claiming real-time duplex conversation anywhere in your slides or script?
- [ ] Is every claim you're making backed by a number you can show, or clearly labeled as roadmap/future work?

## One-Line Pitch (memorize this)

*"We don't just protect the connection — we protect the words that matter most."*
