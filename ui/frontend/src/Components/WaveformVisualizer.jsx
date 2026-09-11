import React, { useRef, useEffect } from "react";

export function WavCanvas({
  color, noise = 0.1, amp = 0.7, speed = 1.5, w = 400, h = 60, clip = false,
}) {
  const ref = useRef(null);
  const off = useRef(0);
  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const ctx = cv.getContext("2d");
    let raf;
    function draw() {
      ctx.clearRect(0, 0, cv.width, cv.height);
      if (clip) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(cv.width/2, cv.height/2, cv.width/2 - 2, 0, Math.PI*2);
        ctx.clip();
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.shadowColor = color; ctx.shadowBlur = 4;
      ctx.beginPath();
      for (let x = 0; x < cv.width; x++) {
        const t = (x + off.current) / cv.width;
        const y = cv.height/2
          + Math.sin(t * Math.PI * 12) * (cv.height/2 - 6) * amp * 0.6
          + Math.sin(t * Math.PI * 5.7) * (cv.height/2 - 6) * amp * 0.3
          + Math.sin(t * Math.PI * 23) * (cv.height/2 - 6) * amp * 0.1
          + (Math.random() - 0.5) * noise * (cv.height * 0.4);
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke(); ctx.shadowBlur = 0;
      if (clip) ctx.restore();
      off.current += speed;
      raf = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(raf);
  }, [color, noise, amp, speed, clip]);
  return <canvas ref={ref} width={w} height={h} style={{ width: "100%", height: h }} />;
}

export function Orb({ label, sub, color, ring, noise, amp }) {
  const D = 180;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="lbl" style={{ marginBottom: 4 }}>{label}</div>
      <div className="relative" style={{
        width: D, height: D, borderRadius: "50%",
        background: "var(--panel-dk)",
        border: `1px solid ${color}40`,
        boxShadow: `0 0 0 1px ${color}22, 0 0 16px ${color}15, inset 0 0 32px rgba(0,0,0,.5)`,
        overflow: "hidden",
      }}>
        {[0.85, 0.65, 0.45].map((r, i) => (
          <div key={i} className="absolute" style={{
            top: `${(1-r)*50}%`, left: `${(1-r)*50}%`,
            width: `${r*100}%`, height: `${r*100}%`,
            borderRadius: "50%",
            border: `1px solid ${color}${i === 0 ? "20" : i === 1 ? "14" : "0A"}`,
          }} />
        ))}
        <div className="absolute" style={{ top:"50%",left:0,right:0,height:1,background:`${color}12` }} />
        <div className="absolute" style={{ left:"50%",top:0,bottom:0,width:1,background:`${color}12` }} />
        <div className="absolute inset-0" style={{ borderRadius:"50%", overflow:"hidden" }}>
          <WavCanvas color={color} noise={noise} amp={amp} speed={1.4} w={D} h={D} />
        </div>
        {Array.from({length:24}).map((_,i) => {
          const a = (i/24)*Math.PI*2;
          const major = i%6===0;
          const r2 = D/2 - (major ? 10 : 5);
          const cx = D/2, cy = D/2;
          return (
            <div key={i} className="absolute" style={{
              width:1, height: major ? 9 : 5,
              background: `${color}${major?"50":"28"}`,
              top: cy + Math.cos(a) * r2 - (major?4.5:2.5),
              left: cx + Math.sin(a) * r2 - 0.5,
              transform: `rotate(${a}rad)`,
              transformOrigin: "50% 0%",
            }} />
          );
        })}
      </div>
      <div className="text-center mt-1">
        <div className="mono font-bold" style={{ fontSize:13, color }}>{sub}</div>
        <div className="lbl" style={{ fontSize:8 }}>{ring}</div>
      </div>
    </div>
  );
}

export function FlowLine({ active }) {
  return (
    <div className="flex-1 flex items-center px-4 relative" style={{ height: 180 }}>
      <div className="w-full relative flex items-center">
        <div className="w-full h-px" style={{ background: `repeating-linear-gradient(90deg, ${active ? "var(--green)" : "var(--red)"} 0, ${active ? "var(--green)" : "var(--red)"} 6px, transparent 6px, transparent 12px)`, opacity:.5 }} />
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center justify-center" style={{
          width:16, height:16, borderRadius:"50%",
          background: active ? "var(--green-a10)" : "var(--red-a10)",
          border: `1px solid ${active ? "var(--green)" : "var(--red)"}`,
          boxShadow: `0 0 8px ${active ? "var(--green-glow)" : "rgba(255,77,95,.3)"}`,
        }}>
          <div className="pulse" style={{ width:6, height:6, borderRadius:"50%", background: active ? "var(--green)" : "var(--red)" }} />
        </div>
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-0.5">
          <div className="lbl" style={{ fontSize:8, color: active ? "var(--green)" : "var(--red)" }}>
            {active ? "PROTECTED" : "DEGRADED"}
          </div>
        </div>
        {[25,75].map(pct => (
          <div key={pct} className="absolute" style={{ left:`${pct}%`, transform:"translateX(-50%)" }}>
            <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
              <path d="M0 4h7M4 1l3 3-3 3" stroke={active?"var(--green)":"var(--red)"} strokeWidth="1" opacity=".6"/>
            </svg>
          </div>
        ))}
      </div>
    </div>
  );
}