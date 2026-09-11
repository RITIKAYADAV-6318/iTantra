import React, { useState, useEffect } from "react";

function padZ(n) { return String(n).padStart(2, "0"); }
function useClock() {
  const [t, setT] = useState(new Date());
  useEffect(() => { const id = setInterval(() => setT(new Date()), 1000); return () => clearInterval(id); }, []);
  return t;
}

function L({ c, pulse }) {
  return <span className={`led led-${c}${pulse ? " pulse" : ""}`} />;
}

export default function Header({ tab, setTab }) {
  const clock = useClock();

  // Dynamic node detection from URL query parameters (e.g., ?node=A or ?node=B)
  const searchParams = new URLSearchParams(window.location.search);
  const currentNode = (searchParams.get("node") || "A").toUpperCase();

  return (
    <header className="flex items-center justify-between px-5 py-3" style={{ background: "var(--panel)", borderBottom: "1px solid var(--border)" }}>
      {/* Left Side: Exact Figma Layout (Bold Icon Box + Text) */}
      <div className="flex items-center gap-3.5">
        <div className="relative flex items-center justify-center w-10 h-10 border-2 border-[var(--cyan)] shadow-[0_0_12px_rgba(6,182,212,0.3)]" style={{ background: "var(--cyan-a10)" }}>
          <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-[var(--cyan)]" />
          <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-[var(--cyan)]" />
          <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-[var(--cyan)]" />
          <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-[var(--cyan)]" />
          <div className="w-4 h-4 rounded-full border-2 border-[var(--cyan)] flex items-center justify-center">
            <div className="w-1.5 h-1.5 bg-[var(--cyan)] rounded-full animate-ping" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <span className="raj font-black tracking-widest text-base drop-shadow-[0_0_8px_rgba(6,182,212,0.5)]" style={{ color: "var(--cyan)" }}>iTANTRA</span>
            <span className="mono font-bold text-xs text-white">V2.4.1</span>
            {/* Dynamic Node Badge */}
            <span className="px-2 py-0.5 bg-[var(--cyan-a10)] border border-[var(--cyan)] text-[var(--cyan)] text-[10px] font-mono font-bold tracking-wider rounded">
              ● NODE {currentNode}
            </span>
          </div>
          <div className="mono font-semibold text-[10px] tracking-wider text-slate-300">
            NEURAL TRANSCEIVER // LOW-BITRATE RADIO LINK
          </div>
          <div className="text-[10px] italic font-serif text-[var(--cyan)] opacity-90 mt-0.5">
            We don't just protect the connection – we defend the truth within it.
          </div>
        </div>
      </div>

      {/* Center Tabs */}
      <div className="flex items-center gap-1 bg-[#080D16] p-1 border border-[#182030]">
        {[
          { id: "live", label: "LIVE TRANSMISSION" },
          { id: "analytics", label: "SYSTEM ANALYTICS" },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="px-4 py-1.5 text-[11px] raj font-extrabold tracking-wider transition-all"
            style={{
              background: tab === t.id ? "var(--cyan-a10)" : "transparent",
              color: tab === t.id ? "var(--cyan)" : "var(--lo)",
              border: tab === t.id ? "1px solid var(--cyan)" : "1px solid transparent",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Right Side: Status & UTC Clock */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <L c="g" pulse />
          <span className="text-[11px] mono font-bold text-emerald-400 tracking-wider">SECURE LINK ACTIVE</span>
        </div>
        <div className="mono text-sm font-bold text-slate-200 text-right">
          <div className="tracking-widest text-[var(--cyan)]">
            {padZ(clock.getUTCHours())}:{padZ(clock.getUTCMinutes())}:{padZ(clock.getUTCSeconds())} <span className="text-[10px] text-slate-400 font-normal">UTC</span>
          </div>
          <div className="text-[9px] font-normal text-slate-400 tracking-wider">
            ISRO GS-04 · 2026-09-11
          </div>
        </div>
      </div>
    </header>
  );
}