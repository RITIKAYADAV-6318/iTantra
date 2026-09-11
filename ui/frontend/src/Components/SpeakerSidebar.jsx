import React from "react";

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

const events = [
  { type: "RADIO CHATTER", conf: "75%", time: "01:15:37 UTC", color: "var(--cyan)" },
  { type: "SIREN DETECTED", conf: "90%", time: "01:15:33 UTC", color: "var(--amber)" },
  { type: "EXPLOSION (NEAR)", conf: "83%", time: "01:15:29 UTC", color: "var(--red, #ef4444)" },
  { type: "RADIO CHATTER", conf: "77%", time: "01:15:25 UTC", color: "var(--cyan)" },
  { type: "AIRCRAFT OVERHEAD", conf: "89%", time: "01:15:21 UTC", color: "var(--amber)" },
  { type: "SIREN DETECTED", conf: "87%", time: "01:15:18 UTC", color: "var(--amber)" },
  { type: "SIREN DETECTED", conf: "90%", time: "01:15:14 UTC", color: "var(--amber)" },
];

export default function SpeakerSidebar() {
  return (
    <div className="flex flex-col gap-3" style={{ minWidth: 280 }}>
      {/* Speaker Profile Card */}
      <div className="card p-3 relative" style={{ borderRadius: 2, background: "var(--panel-dk)", border: "1px solid var(--border-lo)" }}>
        <Corner accent="var(--cyan-a20)" />
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <L c="c" pulse />
            <span className="lbl text-[9px] tracking-widest">SPEAKER PROFILE</span>
          </div>
          <span className="mono text-[9px] text-[var(--green)]">ACTIVE</span>
        </div>

        {/* Operator Box */}
        <div className="p-2.5 mb-3 flex items-center gap-3" style={{ background: "var(--cyan-a10)", border: "1px solid var(--cyan-a20)" }}>
          <div className="w-8 h-8 rounded-full border border-[var(--cyan)] flex items-center justify-center text-[var(--cyan)]">
            👤
          </div>
          <div>
            <div className="raj font-bold text-xs tracking-wider" style={{ color: "var(--cyan)" }}>OPERATOR-7</div>
            <div className="mono text-[8px] text-[var(--lo)]">VERIFIED • D-VECTOR MATCH</div>
          </div>
        </div>

        <div className="mono text-[8px] text-[var(--lo)] mb-1.5">128-DIM EMBEDDING VECTOR</div>
        
        {/* Vector Grid Preview */}
        <div className="grid grid-cols-12 gap-0.5 mb-2">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="h-2" style={{ background: i % 3 === 0 ? "var(--cyan)" : i % 5 === 0 ? "var(--amber)" : "var(--border)", opacity: 0.8 }} />
          ))}
        </div>

        <div className="mono text-[9px] text-[var(--lo)] flex justify-between">
          <span>COSINE SIM: <strong className="text-white">0.987</strong></span>
          <span className="text-[var(--green)]">AUTH: PASS</span>
        </div>
      </div>

      {/* Sound-Event Feed Card */}
      <div className="card p-3 relative flex-1" style={{ borderRadius: 2, background: "var(--panel-dk)", border: "1px solid var(--border-lo)" }}>
        <Corner accent="var(--amber-a10)" />
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
            <span className="lbl text-[9px] tracking-widest text-red-400">SOUND-EVENT FEED</span>
          </div>
          <span className="mono text-[8px] px-1.5 py-0.5 bg-red-950 text-red-400 border border-red-900">LIVE</span>
        </div>

        {/* Event List */}
        <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
          {events.map((ev, index) => (
            <div key={index} className="p-2 flex items-center justify-between" style={{ background: "var(--panel)", border: "1px solid var(--border-lo)" }}>
              <div>
                <div className="raj font-bold text-[10px] tracking-wider" style={{ color: ev.color }}>[{ev.type}]</div>
                <div className="mono text-[8px] text-[var(--lo)]">{ev.time}</div>
              </div>
              <div className="raj font-bold text-sm" style={{ color: ev.color }}>{ev.conf}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}