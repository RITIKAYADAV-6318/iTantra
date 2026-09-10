# Status Board — update this yourself, every day, don't wait to be asked

Status values: `not started` / `stub` / `working (standalone)` / `integrated`

| Module | Owner | Day 1 | Day 2 | Day 3 | Day 4 | Blockers |
|---|---|---|---|---|---|---|
| STT (transcribe + confidence) | | | | | | |
| LID | | | | | | |
| TTS (+ speaker/prosody) | | | | | | |
| Criticality tagger | | | | | | |
| Allocator — greedy | | | | | | |
| Allocator — QIEA | | | | | | |
| Channel simulator | | | | | | |
| Packet schema | | | | | | |
| Sound-event tags | | | | | | |
| FastAPI backend | | | | | | |
| React dashboard | | | | | | |
| Audio playback (before/after) | | | | | | |
| main.py / full pipeline end-to-end | | | | | | |

## Evening demo log
One line per person per day: what you showed working, live, today.

- Day 1: STT — using faster-whisper (not IndicConformer) — IndicConformer requires
  NeMo/Linux setup, revisit later if time allows. Same transcribe() contract either way.
- Day 2:
- Day 3: (mandatory full end-to-end checkpoint — must pass before Day 4 starts)
- Day 4:
