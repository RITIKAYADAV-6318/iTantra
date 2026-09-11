# iTantra — SIH26173

Neural transceiver: voice communication over extremely low-bitrate, noisy radio links,
via criticality- and confidence-aware STT → adaptive bit allocation → TTS.

## Repo Structure

```
iTantra-repo/
├── contracts/               # Module communication contracts — READ THIS FIRST
│   ├── interfaces.md        # Plain-English spec of every module boundary
│   └── schemas.py           # Enforced Pydantic versions of the same contracts
├── tests/
│   └── test_contracts.py    # Run before every integration/merge
├── stt/                     # Speech-to-Text: audio -> (text, per-token confidence)
├── tts/                     # Text-to-Speech: text + speaker/prosody -> audio
├── channel/                 # Bad-radio-link simulator + packet schema
├── allocator/               # Criticality tagger + greedy/QIEA bit allocator (CORE USP)
├── ui/
│   ├── backend/             # FastAPI bridge: exposes pipeline as HTTP endpoints
│   │                        # + serves audio as base64 for the before/after players
│   ├── frontend/            # React dashboard (Vite) — PRIMARY UI for the demo
│   └── streamlit_fallback/  # Cheap backup dashboard in case React integration slips
├── docs/                    # Build plan, status board, pitch materials
│   └── SCREEN_ARCHITECTURE.md  # UI wireframe, panel map, sender/receiver Node concept
└── main.py                  # Wires everything into one Sender -> Channel -> Receiver run
                              # (useful for backend-only testing without the UI)
```

## Tech Stack (locked)

Python, **faster-whisper "small"** (STT — see decision note below), **Coqui TTS
xtts_v2** (TTS — see decision note below), SpeechBrain/Resemblyzer (speaker
embeddings, if used separately from xtts_v2's built-in voice cloning), librosa
(prosody), custom criticality tagger + allocator, custom channel simulator, FastAPI
(pipeline bridge), React + recharts (dashboard), Streamlit (fallback dashboard),
Git/GitHub.

**STT decision note:** AI4Bharat IndicConformer was the original plan but requires
NVIDIA's NeMo toolkit (AI4Bharat's own fork), which needs a Linux/WSL setup and a
non-trivial build — too much installation risk for Day 1. Switched to
`faster-whisper` ("small" model, locked given the time constraint), which satisfies
the exact same `transcribe()` contract in `contracts/schemas.py` and already returns
real per-word confidence via `word.probability`. Same-day, same-file swap if revisited.

**TTS decision note:** AI4Bharat Indic-TTS was the original plan but has its own
custom setup (repo clone, manual checkpoint pulls) — same category of install risk
as IndicConformer, just less severe. Switched to Coqui TTS's `xtts_v2` model, which
installs with a plain `pip install TTS` and does voice-cloning-style synthesis from a
short reference clip — a good fit for the "sounds like the real speaker" USP. Verify
both demo languages work cleanly on the team's actual install before relying on it
for the live demo, same protocol as the STT check.

**Explicitly not in scope:** ONNX Runtime, GNU Radio/SDR hardware, Raspberry Pi/Jetson,
torchaudio, gRPC, BPE+entropy coding, FEC, post-quantum signatures. These are roadmap/
slide claims only — see `docs/BUILD_PLAN.md` for why each was cut.

## Running the full stack (once modules are real, not just stubs)

```bash
# Terminal 1 — backend
source venv/bin/activate
uvicorn ui.backend.api:app --reload --port 8000

# Terminal 2 — frontend
cd ui/frontend
npm install
npm run dev
# open http://localhost:5173
```

Fallback if React isn't ready:
```bash
streamlit run ui/streamlit_fallback/dashboard.py
```

## Module Contracts (agreed Day 1 — do not change without telling Integration Lead)

**Read `contracts/interfaces.md` first** — that's the full, plain-English contract for
every module boundary (STT→Allocator, Allocator→Packet, Packet→Channel→TTS,
Backend→UI). `contracts/schemas.py` is the enforced version (Pydantic models) —
import from there in your module so a broken contract fails immediately as a code
error, not silently at integration time.

Quick reference (see `contracts/interfaces.md` for the full field-by-field spec):

```python
# stt/stt.py
def transcribe(audio_chunk) -> tuple[str, list[float]]:
    """Returns (text, confidence_per_token). confidence in [0,1]."""

# allocator/criticality.py
def tag_criticality(text: str) -> list[float]:
    """Returns criticality_per_token, aligned 1:1 with tokens in text. [0,1]."""

# allocator/allocate.py
def allocate(text: str, confidence: list[float], criticality: list[float],
             channel_bitrate_kbps: float) -> dict:
    """Returns a packet dict: see channel/packet.py / contracts/schemas.py for schema."""

# tts/tts.py
def synthesize(text: str, speaker_embedding, prosody_vector) -> "audio":
    """Returns audio (WAV bytes) in speaker's voice/tone."""

# channel/simulator.py
def send(packet: dict, bitrate_kbps: float, noise_level: float) -> dict:
    """Simulates a bad channel. Returns (possibly degraded) packet."""
```

**Rule:** if you need to change a contract, post it in the team channel, update
`contracts/interfaces.md`'s change log, and update `contracts/schemas.py` — all in the
same commit. Nobody else should discover a contract change because their code broke.

**Before every integration/merge:** run `python tests/test_contracts.py` — it validates
that STT, allocator, and backend outputs still match the frozen contracts.

## Daily Workflow

- **Morning sync (10 min):** each person states what they're building today + what they
  need from someone else's module.
- **End of day (10-15 min):** each person demos what *runs*, live — not a status update.
- **Every evening:** run `main.py` end-to-end with whatever exists (stubs fill gaps).
  If it doesn't run, fix that before starting new work tomorrow.
- **Status board:** `docs/STATUS.md` — update it yourself, don't wait to be asked.

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Each module also has its own `requirements.txt` — merge into the root one as you add
dependencies, and mention it in your commit message.
