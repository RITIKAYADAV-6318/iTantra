import React, { useState } from "react";
import { WavCanvas } from "./WaveformVisualizer";

function Corner({ accent = "var(--cyan-a20)" }) {
  return (
    <div className="absolute inset-0 pointer-events-none">
      <div style={{ position: "absolute", top: 0, left: 0, width: 8, height: 8, borderTop: "1px solid " + accent, borderLeft: "1px solid " + accent }} />
      <div style={{ position: "absolute", top: 0, right: 0, width: 8, height: 8, borderTop: "1px solid " + accent, borderRight: "1px solid " + accent }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, width: 8, height: 8, borderBottom: "1px solid " + accent, borderLeft: "1px solid " + accent }} />
      <div style={{ position: "absolute", bottom: 0, right: 0, width: 8, height: 8, borderBottom: "1px solid " + accent, borderRight: "1px solid " + accent }} />
    </div>
  );
}

function L({ c, pulse }) {
  return <span className={`led led-${c}${pulse ? " pulse" : ""}`} />;
}

function AudioPlayer({ label, color, noisy, playing, onToggle }) {
  const btnBg = playing ? color + "18" : "var(--dim)";
  const btnBorder = playing ? color : "var(--border)";

  return (
    <div className="flex items-center gap-3 py-2 px-3" style={{ background: "var(--panel-dk)", border: "1px solid var(--border-lo)" }}>
      <button
        onClick={onToggle}
        className="flex-shrink-0 flex items-center justify-center"
        style={{ width: 28, height: 28, borderRadius: 2, background: btnBg, border: "1px solid " + btnBorder, color }}
      >
        <span style={{ fontSize: 9 }}>{playing ? "■" : "▶"}</span>
      </button>
      <div className="lbl" style={{ minWidth: 120, color }}>{label}</div>
      <div className="flex-1 inset overflow-hidden" style={{ height: 28, padding: "2px 4px" }}>
        {playing ? (
          <WavCanvas color={color} noise={noisy ? 0.9 : 0.06} amp={noisy ? 0.75 : 0.88} speed={noisy ? 2 : 1.5} h={22} />
        ) : (
          <div className="w-full h-full flex items-center"><div className="w-full h-px" style={{ background: "var(--border)" }} /></div>
        )}
      </div>
      <div className="mono" style={{ fontSize: 9, color: "var(--lo)", minWidth: 32 }}>{playing ? "0:08" : "—"}</div>
    </div>
  );
}

const ACC = {
  c: { c: "var(--cyan)", bg: "var(--cyan-a10)", led: "c" },
  a: { c: "var(--amber)", bg: "var(--amber-a10)", led: "a" },
  b: { c: "var(--blue)", bg: "var(--blue-a10)", led: "c" },
  g: { c: "var(--green)", bg: "var(--green-a10)", led: "g" },
};

function PathNode({ label, sub, acc }) {
  const { c, bg, led } = ACC[acc];
  return (
    <div className="relative flex flex-col items-center gap-1 px-3 py-2" style={{ border: "1px solid " + c + "35", background: bg, minWidth: 76 }}>
      <Corner accent={c + "28"} />
      <div className="flex items-center gap-1.5">
        <L c={led} pulse />
        <span className="raj" style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".1em", color: c }}>{label}</span>
      </div>
      {sub && <span className="lbl" style={{ fontSize: 7.5 }}>{sub}</span>}
    </div>
  );
}

function Arrow({ color }) {
  return (
    <div className="flex-1 flex items-center">
      <div className="flex-1 h-px" style={{ background: color, opacity: 0.4 }} />
      <svg width="6" height="6" viewBox="0 0 6 6"><path d="M0 3h5M3 1l2 2-2 2" stroke={color} strokeWidth="1" opacity="0.7" /></svg>
    </div>
  );
}

export default function AudioPlayerSection({ noise }) {
  const [playing1, setPlaying1] = useState(false);
  const [playing2, setPlaying2] = useState(false);

  return (
    <div className="flex flex-col gap-2" style={{ minWidth: 240 }}>
      <div className="lbl mb-1">AUDIO PLAYBACK COMPARISON</div>
      <AudioPlayer
        label="BEFORE — Normal Call"
        color="#f59e0b"
        noisy
        playing={playing1}
        onToggle={() => setPlaying1(p => !p)}
      />
      <AudioPlayer
        label="AFTER — iTantra Mode"
        color="#06b6d4"
        noisy={false}
        playing={playing2}
        onToggle={() => setPlaying2(p => !p)}
      />
      <div className="card p-3 relative flex-1" style={{ borderRadius: 2 }}>
        <Corner accent="var(--amber-a10)" />
        <div className="lbl mb-2" style={{ fontSize: 8 }}>SIGNAL PATH</div>
        <div className="flex items-center gap-1 flex-wrap">
          <PathNode label="MIC" sub="IN" acc="c" />
          <Arrow color="var(--cyan)" />
          <PathNode label="ENC" sub="GSM-HR" acc="c" />
          <Arrow color="var(--amber)" />
          <PathNode label="RF" sub="3.5k" acc="a" />
          <Arrow color="var(--amber)" />
          <PathNode label="NOISE" sub={`${noise}%`} acc="a" />
          <Arrow color="var(--blue)" />
          <PathNode label="NEURAL" sub="RX-V2" acc="b" />
          <Arrow color="var(--green)" />
          <PathNode label="OUT" sub="PCM" acc="g" />
        </div>
      </div>
    </div>
  );
}