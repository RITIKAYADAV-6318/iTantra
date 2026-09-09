# iTantra — SIH26173

Neural transceiver: voice communication over extremely low-bitrate, noisy radio links,
via criticality- and confidence-aware STT → adaptive bit allocation → TTS.

## Repo Structure

```
iTantra-repo/
├── stt/          # Speech-to-Text: audio -> (text, per-token confidence)
├── tts/          # Text-to-Speech: text + speaker/prosody -> audio
├── channel/      # Bad-radio-link simulator + packet schema
├── allocator/    # Criticality tagger + greedy/QIEA bit allocator (CORE USP)
├── ui/           # Dashboard: bitrate meter, before/after toggle, slider
├── docs/         # Build plan, status board, pitch materials
└── main.py       # Wires everything into one Sender -> Channel -> Receiver run
```

## Locked Interfaces (agreed Day 1 — do not change without telling Integration Lead)

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
    """Returns a packet dict: see channel/packet.py for schema."""

# tts/tts.py
def synthesize(text: str, speaker_embedding, prosody_vector) -> "audio":
    """Returns audio (numpy array or bytes) in speaker's voice/tone."""

# channel/simulator.py
def send(packet: dict, bitrate_kbps: float, noise_level: float) -> dict:
    """Simulates a bad channel. Returns (possibly degraded) packet."""
```

**Rule:** if you need to change an interface, post it in the team channel and update this
file in the same commit. Nobody else should discover an interface change by their code
breaking.

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
