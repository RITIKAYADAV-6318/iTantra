# Screen Architecture

**Answers, up front:** there is **one screen design**, not separate sender/receiver
screens. Every device that runs iTantra runs this exact same screen. What changes
between devices is only a label (`NODE A`, `NODE B`, ...) and which panel is actively
lit up at a given moment — never the layout, never the feature set.

This matters because real radio communication is duplex: whoever's listening right
now will be talking a minute from now. If you build a "sender screen" and a separate
"receiver screen," you've hard-coded a role that doesn't actually exist in the real
system — and you'd have to rebuild the UI the moment someone wants to talk back.

---

## How many screens: 2

**Updated Day 1: originally 1 screen, now 2 — one live, one analytics.** A team
member built a detailed rough prototype (token-stream monitor, speaker profile,
sound-event feed, benchmark stats) that's genuinely strong but too dense for a
single live-demo screen. The fix isn't to cut those features — it's to split by
*when they're needed*, not remove them:

- **Live Transmission** — what's on screen during the actual live demo moment.
  Controls, bitrate gauge, the two-orb transmission visualizer, before/after audio,
  protection chart. Calm, minimal, one primary action button. This is what judges
  watch during the 90-second core "wow" beat — it should be the least cluttered
  thing on stage.
- **Analytics** — shown after the live moment, during explanation/Q&A. Run history,
  packet-size trend chart, run log table. Denser is fine here, since nobody's
  watching a live moment while you're on this tab. (Speaker profile and sound-event
  feed from the original prototype belong here too, once wired to real data — see
  note below.)

A third screen isn't worth it — more navigation is more that can go wrong live, and
the plan protects rehearsal time over UI polish.

**On the sound-event feed specifically:** if it's showing mocked/random entries
rather than a real detector, don't present it live as if it's working — a judge
asking "what triggered that" and getting "nothing, it's decorative" costs more trust
than not showing it. Either wire it to a real (even simple) detector before demo day,
or keep it as a slide claim, not a live panel.

---

## Wireframe (text mockup)

```
┌─────────────────────────────────────────────────────────────────┐
│  iTANTRA                                          ● NODE A       │
│  "We don't just protect the connection — we..."                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   [ ● BASELINE ]  [ ● iTANTRA MODE ]      ╭──────╮   bitrate     │
│                                            │ 5.0  │   ─────────  │
│                                            │ kbps │   noise ──   │
│                                            ╰──────╯               │
│                                                                   │
│              [ ▶  RUN DEMO SENTENCE  ]                            │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│   LANGUAGE        MODE            PACKET SIZE                    │
│   HI               iTANTRA         214 B                         │
├─────────────────────────────────────────────────────────────────┤
│   "send backup to grid reference four seven two nine"            │
├─────────────────────────────────────────────────────────────────┤
│   ● BEFORE — normal call, no protection                          │
│   [ ▶───────────────────────────────────── ]                     │
│   ● AFTER — iTantra mode                                         │
│   [ ▶───────────────────────────────────── ]                     │
├─────────────────────────────────────────────────────────────────┤
│   BANDWIDTH PROTECTION PER WORD                                  │
│   █▁█▁█████▁▁▁  (bar chart, one bar per word)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Two-orb transmission visualizer

A dedicated visual for the "wow" moment: two orbs, **ORIGINAL MESSAGE** (left) and
**iTANTRA OUTPUT** (right, or **RECEIVED — DEGRADED** in baseline mode), with a
connecting line between them.

**Rule: the glow is driven by real audio playback state, not a timer or fake
animation.** The left orb glows only while the "before" `<audio>` element is
actually playing; the right orb glows only while the "after" `<audio>` element is
actually playing. A traveling pulse runs along the connecting line, colored red for
baseline (degrading) or cyan for iTantra (protected), only while something is
actually transmitting. If it's not playing, it's not glowing — same clarity rule as
everything else on this screen.

Implementation: `AudioPlayer.jsx` exposes `onPlayingChange` from the real
`<audio>` element's play/pause/ended events; `App.jsx` lifts that into
`senderPlaying` / `receiverPlaying` state and passes it to
`TransmissionVisualizer.jsx`.

---

## Feature-to-panel map

| Panel | Features | Component file |
|---|---|---|
| Header | Node label, USP tagline, online status dot | `App.jsx` (inline) |
| Tab nav | Live Transmission / Analytics switch | `App.jsx` (inline) |
| Controls (Live) | Mode toggle, bitrate gauge, bitrate slider, noise slider, run button | `ModeToggle.jsx`, `RadialGauge.jsx`, `BitrateSlider.jsx` |
| Transmission visualizer (Live) | Two orbs glowing in sync with real audio playback | `TransmissionVisualizer.jsx` |
| Status row (Live) | Detected language, active mode, packet size | `App.jsx` (inline) |
| Transcript (Live) | Transcribed / reconstructed text | `App.jsx` (inline) |
| Transmission log (Live) | Before/after audio playback | `AudioPlayer.jsx` (×2) |
| Protection chart (Live) | Per-word bandwidth protection bar chart | `ProtectionChart.jsx` |
| Run history chart (Analytics) | Packet size trend across runs this session | `App.jsx` (inline, recharts) |
| Run log table (Analytics) | Mode/bitrate/packet size per run | `App.jsx` (inline) |
| Benchmark note (Analytics) | Points to WER/QIEA numbers in the pitch deck | `App.jsx` (inline) |

Nothing on this screen is decorative. If a future addition (confidence highlighting,
sound-event badges) doesn't map to a real, live value from the backend, it doesn't
belong here — see `docs/BUILD_PLAN.md`'s clarity checklist.

---

## The Node concept — how sender/receiver actually works

Every instance of this screen can be opened with a URL query parameter:

```
http://localhost:5173/?node=A
http://localhost:5173/?node=B
```

The app reads `node` from the URL and displays it in the header badge. That's the
**only** difference between "Node A" and "Node B" — same controls, same panels, same
pipeline calls. Whichever node runs "Run demo sentence" is acting as sender for that
utterance; the other node would show the received result if the backend were wired
to push data between them (see below — not required for the current demo script).

### For the one-laptop demo (what you're actually doing)

Open two browser windows side by side on the same laptop:
- Left window: `http://localhost:5173/?node=A`
- Right window: `http://localhost:5173/?node=B`

Both talk to the same local FastAPI backend (`http://localhost:8000`). For the
rehearsed demo script (toggle mode, run, compare before/after), you only need **one**
window actively driving the pipeline — the second window exists to visually sell the
"two independent devices" story during the pitch, exactly as discussed in the earlier
demo-script planning. You are not required to wire live cross-node message passing for
this to work; running one node and narrating "this is what Node B would receive" is
enough for the 4-day scope.

### If you want real cross-node data flow (stretch, not required)

This would mean Node A's "Run demo sentence" result actually appears on Node B's
screen automatically. That requires a small addition — a shared state (e.g. the
backend keeps the last result in memory, or a simple WebSocket) that both browser
windows poll or subscribe to. **This is explicitly a stretch goal, not part of the
4-day core scope** — the current one-node-drives-the-narration approach is sufficient
and lower-risk for the live demo.

### Scaling to 2+ real physical devices (future, post-hackathon)

Nothing about the screen changes. Each physical device (laptop, Raspberry Pi, radio
terminal) runs:
- its own copy of the React frontend
- its own copy of the FastAPI backend
- its own copy of the STT/TTS/allocator pipeline

The only thing that changes moving from "software channel simulator on one laptop" to
"real devices over a real radio link" is what sits inside `channel/simulator.py` — it
gets swapped for a real transport layer (actual radio hardware, or a network socket
between two machines). The UI, the backend API shape, and the contracts in
`contracts/interfaces.md` don't need to change at all. This is one of the reasons the
contracts-first approach matters: the screen and the pipeline are already built to be
node-agnostic, so scaling up later is a transport-layer swap, not a redesign.

---

## Clarity rules for this screen (do not violate these while building)

1. Every element must map to a real, live value — no decoration.
2. One primary action button (`RUN DEMO SENTENCE`) — no competing calls to action.
3. Big, legible numbers (bitrate, packet size, language) — readable from the back of
   a room on a projector.
4. Dark background, single accent color (cyan-blue) for anything "good/active,"
   red only for the baseline/failure state — no rainbow of colors competing for
   attention.
5. No page navigation, no hidden panels — everything needed for the demo is visible
   at once, in the order the demo script uses it (controls → run → result → audio →
   chart, top to bottom).
