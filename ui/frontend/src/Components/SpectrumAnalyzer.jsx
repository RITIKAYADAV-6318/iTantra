import React, { useState, useEffect } from "react";

const FREQ_LABELS = ["63Hz","125","250","500","1k","2k","3k","4k","5k","6k","8k","10k","12k","14k","16k","20k"];

export function Spectrum() {
  const [bars, setBars] = useState(() => FREQ_LABELS.map((_, i) => {
    const base = i < 3 ? 18 : i < 7 ? 60 : i < 12 ? 42 : 18;
    return base + Math.random()*18;
  }));
  const [peaks, setPeaks] = useState(bars.slice());
  useEffect(() => {
    const id = setInterval(() => {
      setBars(prev => {
        const n = prev.map((b, i) => {
          const base = i<3?18:i<7?60:i<12?42:18;
          return Math.max(5, Math.min(90, b+(Math.random()-.47)*10+(base-b)*.06));
        });
        setPeaks(pk => pk.map((p,i) => Math.max(n[i], p*.96)));
        return n;
      });
    }, 110);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="relative" style={{ height:96 }}>
      {[25,50,75].map(g => (
        <div key={g} className="absolute left-0 right-0 flex items-center" style={{ bottom:`${g}%`, zIndex:0 }}>
          <div className="flex-1 h-px" style={{ background:"var(--border-lo)" }} />
          <span className="lbl px-1" style={{ fontSize:7 }}>{g===25?"-36":g===50?"-24":"-12"}dB</span>
        </div>
      ))}
      <div className="flex items-end gap-[2px] h-full" style={{ position:"relative",zIndex:1 }}>
        {bars.map((h,i) => (
          <div key={i} className="flex-1 flex flex-col items-center justify-end h-full relative">
            <div className="absolute w-full" style={{
              bottom:`${peaks[i]}%`, height:1,
              background: peaks[i]>78?"var(--red)":peaks[i]>55?"var(--amber)":"var(--cyan)",
              opacity:.7,
            }} />
            <div className="w-full transition-all duration-100" style={{
              height:`${h}%`,
              borderRadius:"1px 1px 0 0",
              background: h>78
                ? "linear-gradient(to top,var(--amber),var(--red))"
                : h>52
                ? "linear-gradient(to top,var(--blue) 0%,var(--cyan) 100%)"
                : "linear-gradient(to top,#152035 0%,var(--blue) 100%)",
              boxShadow: h>52?"0 0 3px rgba(0,200,255,.2)":"none",
            }} />
          </div>
        ))}
      </div>
    </div>
  );
}

const WORDS = [
  { word:"send",     pct:25, ok:false },   // filler → low
  { word:"backup",   pct:75, ok:true  },   // keyword → high
  { word:"to",       pct:30, ok:false },   // filler → low
  { word:"grid",     pct:80, ok:true  },   // keyword → high
  { word:"reference",pct:45, ok:false },   // neutral → medium
  { word:"four",     pct:95, ok:true  },   // number → max
  { word:"seven",    pct:92, ok:true  },   // number → max
  { word:"two",      pct:94, ok:true  },   // number → max
  { word:"nine",     pct:93, ok:true  },   // number → max
];


export function BandwidthChart() {
  return (
    <div className="flex flex-col gap-1">
      {WORDS.map(({ word, pct, ok }) => (
        <div key={word} className="flex items-center gap-2">
          <div className="mono" style={{ fontSize:9, minWidth:64, color:"var(--mid)", textAlign:"right" }}>{word}</div>
          <div className="flex-1 relative" style={{ height:12 }}>
            <div className="absolute inset-0" style={{ background:"var(--border-lo)", borderRadius:1 }} />
            <div className="absolute top-0 left-0 h-full transition-all" style={{
              width:`${pct}%`, borderRadius:1,
              background: ok ? "var(--green)" : "var(--red)",
              boxShadow: ok ? "0 0 4px var(--green-glow)" : "0 0 4px rgba(255,77,95,.3)",
              opacity:.75,
            }} />
            <div className="absolute right-1 top-0 h-full flex items-center">
              <span className="mono" style={{ fontSize:8, color: ok?"var(--green)":"var(--red)" }}>{pct}%</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}