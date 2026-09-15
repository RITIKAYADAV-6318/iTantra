import { useState } from "react";
import Header from "./Components/Header";
import TelemetryGrid from "./Components/TelemetryGrid";
import TrajectoryChart from "./Components/TrajectoryChart";
import { Orb, FlowLine } from "./Components/WaveformVisualizer";
import AudioPlayerSection from "./Components/AudioPlayerSection";
import { Spectrum, BandwidthChart } from "./Components/SpectrumAnalyzer";
import SpeakerSidebar from "./Components/SpeakerSidebar";

function L({ c, pulse }) {
  return <span className={`led led-${c}${pulse ? " pulse" : ""}`} />;
}

function Corner({ accent = "var(--cyan-a20)" }) {
  return (
    <>
      <div style={{ position:"absolute",top:0,left:0,width:8,height:8,borderTop:`1px solid ${accent}`,borderLeft:`1px solid ${accent}` }} />
      <div style={{ position:"absolute",top:0,right:0,width:8,height:8,borderTop:`1px solid ${accent}`,borderRight:`1px solid ${accent}` }} />
      <div style={{ position:"absolute",bottom:0,left:0,width:8,height:8,borderBottom:`1px solid ${accent}`,borderLeft:`1px solid ${accent}` }} />
      <div style={{ position:"absolute",bottom:0,right:0,width:8,height:8,borderBottom:`1px solid ${accent}`,borderRight:`1px solid ${accent}` }} />
    </>
  );
}

function Lbl({ children }) {
  return <span className="lbl">{children}</span>;
}

const FREQ_LABELS = ["63Hz","125","250","500","1k","2k","3k","4k","5k","6k","8k","10k","12k","14k","16k","20k"];

const SNR_DATA = (pipelineResult) => {
  const confidence = pipelineResult?.confidence_per_token || [];
  const protection = pipelineResult?.protection_per_token || [];

  const length = Math.max(confidence.length, protection.length);

  if (!length) return [];

  return Array.from({ length }, (_, i) => ({
    t: `${i + 1}`,
    itantra: Math.round((protection[i] ?? 0) * 100),
    baseline: Math.round((confidence[i] ?? 0) * 100),
  }));
};

const EVENTS = [
  { ts:"14:32:35", type:"WARNING",   color:"var(--amber)", msg:"Latency spike detected: 4.1 ms" },
  { ts:"14:32:20", type:"PROTECTED", color:"var(--green)", msg:"AVC handshake complete — Node A" },
  { ts:"14:32:07", type:"PROTECTED", color:"var(--green)", msg:"Packet stream authenticated" },
  { ts:"14:31:58", type:"WARNING",   color:"var(--amber)", msg:"SNR degradation on Node C: −6.7 dB" },
  { ts:"14:31:45", type:"ALERT",     color:"var(--red)",   msg:"Intrusion attempt blocked — GS-04" },
  { ts:"14:31:22", type:"PROTECTED", color:"var(--green)", msg:"Neural reconstruction: 98.4% corr." },
  { ts:"14:31:09", type:"WARNING",   color:"var(--amber)", msg:"Node E link timeout — reconnecting" },
  { ts:"14:30:54", type:"PROTECTED", color:"var(--cyan)",  msg:"Bitrate stable 3.5 kbps · AES-256" },
];

const NODES = [
  { id:"A", status:"ONLINE",  led:"g", gain:"+19.4 dB", loss:"0.02%", lat:"12ms" },
  { id:"B", status:"ONLINE",  led:"g", gain:"+18.2 dB", loss:"0.04%", lat:"15ms" },
  { id:"C", status:"DEGRADED",led:"a", gain:"+11.5 dB", loss:"1.20%", lat:"38ms" },
  { id:"D", status:"ONLINE",  led:"g", gain:"+17.9 dB", loss:"0.07%", lat:"11ms" },
  { id:"E", status:"OFFLINE", led:"r", gain:"—",         loss:"—",     lat:"—"    },
];

function SecHead({ led, children }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      {led && <L c={led} pulse={led==="c"||led==="g"} />}
      <span className="raj" style={{ fontSize:11, fontWeight:700, letterSpacing:".18em", textTransform:"uppercase", color:"var(--mid)" }}>{children}</span>
    </div>
  );
}

function LiveView({
  mode,
  setMode,
  noise,
  setNoise,
  bitrate,
  setBitrate,
  selectedFile,
  setSelectedFile,
  pipelineLoading,
  setPipelineLoading,
  pipelineResult,
  setPipelineResult,
}) 

{
  const runUploadedAudio = async (file) => {
    try {
      setPipelineLoading(true);
      setPipelineResult(null);

      const buffer = await file.arrayBuffer();

      let binary = "";
      const bytes = new Uint8Array(buffer);

      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
      }

      const audioBase64 = btoa(binary);

      const response = await fetch("http://localhost:8000/run_pipeline", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          audio_base64: audioBase64,
          bitrate_kbps: bitrate,
          noise_level: noise,
          mode: mode,
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const result = await response.json();
      setPipelineResult(result);
    } catch (error) {
      console.error("Pipeline error:", error);
      alert("Audio processing failed. Check that the backend is running.");
    } finally {
      setPipelineLoading(false);
    }
  };


 const transcriptWords = pipelineResult?.text
  ? pipelineResult.text.split(" ").map((word, index) => ({
      w: word,
      pct: Math.round((pipelineResult?.confidence_per_token?.[index] ?? 0) * 100),
     ok: (pipelineResult?.protection_per_token?.[index] ?? 0) >= 0.7,
    }))
  : [];

  return (
    <div className="flex flex-col gap-3 overflow-auto flex-1" style={{ padding:"12px 16px" }}>
      {/* Top Control Bar */}
      <div className="card relative flex flex-wrap items-center justify-between gap-4 p-4" style={{ borderRadius:2 }}>
        <Corner />
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex flex-col gap-1">
            <Lbl>Operation Mode</Lbl>
            <div className="flex items-center gap-2 mt-1">
              {(["baseline","itantra"]).map(m => (
                <button key={m} onClick={()=>setMode(m)}
                  className="relative flex items-center gap-2 px-3 py-1.5"
                  style={{
                    border:`1px solid ${mode===m?(m==="itantra"?"var(--cyan)":"var(--amber)"):"var(--border)"}`,
                    background:mode===m?(m==="itantra"?"var(--cyan-a10)":"var(--amber-a10)"):"transparent",
                    boxShadow:mode===m?`0 0 6px ${m==="itantra"?"var(--cyan-glow)":"var(--amber-glow)"}`:"inset 0 1px 3px rgba(0,0,0,.5)",
                    cursor:"pointer",
                  }}
                >
                  <div style={{
                    width:20, height:10, borderRadius:5, position:"relative",
                    background:mode===m?(m==="itantra"?"var(--cyan-a10)":"var(--amber-a10)"):"var(--dim)",
                    border:`1px solid ${mode===m?(m==="itantra"?"var(--cyan)":"var(--amber)"):"var(--border)"}`,
                  }}>
                    <div style={{
                      position:"absolute", top:1,
                      left:mode===m?9:1, width:6, height:6, borderRadius:3,
                      background:mode===m?(m==="itantra"?"var(--cyan)":"var(--amber)"):"var(--lo)",
                      boxShadow:mode===m?`0 0 4px ${m==="itantra"?"var(--cyan)":"var(--amber)"}`:"none",
                      transition:"left .15s",
                    }} />
                  </div>
                  <span className="raj" style={{ fontSize:11, fontWeight:700, letterSpacing:".1em", color:mode===m?(m==="itantra"?"var(--cyan)":"var(--amber)"):"var(--lo)" }}>
                    {m==="baseline"?"BASELINE":"iTANTRA"}
                  </span>
                </button>
              ))}
            </div>
          </div>

                   <div className="flex flex-col gap-1 px-4 py-1" style={{ borderLeft:"1px solid var(--border)", borderRight:"1px solid var(--border)", minWidth:140 }}>
            <div className="flex justify-between items-center">
              <Lbl>Bitrate</Lbl>
              <span className="mono font-bold gc" style={{ fontSize:14 }}>
                {bitrate.toFixed(1)}<span className="lbl ml-0.5" style={{ fontSize:8 }}>kbps</span>
              </span>
            </div>
          
          </div>

          <div className="flex flex-col gap-1 flex-1 min-w-[200px] px-2">
            <div className="flex justify-between items-center">
              <Lbl>AWGN Noise Level</Lbl>
             <span className="mono font-bold ga" style={{ fontSize:14 }}>
  {(noise * 100).toFixed(0)}
  <span className="lbl ml-0.5" style={{fontSize:8}}>%</span>
</span>
            </div>
           <input
  type="range"
  min={0}
  max={1}
  step={0.01}
  value={noise}
  onChange={e=>setNoise(+e.target.value)}
  className="slider w-full mt-1"
/>
          </div>
        </div>

        <div>
          <button  onClick={() => document.getElementById("audio-upload").click()} className="relative px-5 py-2.5 raj font-bold" style={{
            fontSize:12, letterSpacing:".16em",
            background:"linear-gradient(180deg,rgba(0,200,255,.22) 0%,rgba(0,200,255,.10) 100%)",
            border:"1px solid var(--cyan)",
            color:"var(--cyan)",
            boxShadow:"0 0 14px var(--cyan-glow), inset 0 1px 0 rgba(0,200,255,.2), inset 0 -1px 0 rgba(0,0,0,.5)",
          }}>
            <Corner accent="var(--cyan)" />
           ↥&nbsp; UPLOAD AUDIO
          </button>
          <input
  id="audio-upload"
  type="file"
  accept="audio/*"
  className="hidden"
  onChange={(e) => {
  const file = e.target.files?.[0];

  if (file) {
    setSelectedFile(file);
    runUploadedAudio(file);
  }
}}
/>
        </div>
      </div>

      {/* Waveform / Orb Section */}
      <div className="card relative flex items-center justify-center py-4 px-4" style={{ borderRadius:2 }}>
        <Corner />
        <Orb label="ORIGINAL ACTUAL MESSAGE" sub="SNR 9.2 dB" color="#f59e0b" ring="HIGH NOISE · DEGRADED" noise={0.9} amp={0.65} />
        <FlowLine active={mode === "itantra"} />
        <Orb label="iTANTRA CLEAN RECONSTRUCTION" sub="SNR 28.6 dB" color={mode === "itantra" ? "#10b981" : "#64748b"} ring={mode === "itantra"
  ? `${Math.round(((pipelineResult?.protection_per_token || []).filter(v => v >= 0.7).length / (pipelineResult?.protection_per_token?.length || 1)) * 100)}% PROTECTED`
  : "BASELINE — NO RECONSTRUCTION"} noise={mode === "itantra" ? 0.05 : 0.7} amp={mode === "itantra" ? 0.88 : 0.5} />
      </div>

      {/* Audio Player Section with Full Width */}
      <AudioPlayerSection
  noise={noise}
  pipelineResult={pipelineResult}
  pipelineLoading={pipelineLoading}
   selectedFile={selectedFile}
/>

      {/* Bottom Section Split: Left 4 Stacked Blocks & Right Transcript/Bandwidth Chart */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
        {/* Left Stacked Meta/Info Blocks (4 Blocks vertically) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          {[
            {k:"LANGUAGE", v:pipelineResult?.language ? pipelineResult.language.toUpperCase() : "—", c:"var(--cyan)"},
            { k:"MODE",        v:mode==="itantra"?"iTANTRA":"BASELINE", c:mode==="itantra"?"var(--cyan)":"var(--amber)" },
          {k:"PACKET SIZE", v:pipelineResult?.packet_bytes ? `${pipelineResult.packet_bytes} B` : "—", c:"var(--mid)"},
            { k:"CHANNEL",     v:"UHF-04",         c:"var(--blue)"  },
          ].map(({ k, v, c }) => (
            <div key={k} className="card px-3 py-3 relative" style={{ borderRadius:2 }}>
              <Corner accent="var(--cyan-a10)" />
              <div className="lbl">{k}</div>
              <div className="raj font-bold" style={{ fontSize:13, color:c, marginTop:2 }}>{v}</div>
            </div>
          ))}
        </div>

        {/* Right Transcript & Chart Full Expansion */}
        <div className="md:col-span-8 card relative p-4 flex flex-col" style={{ borderRadius:2 }}>
          <Corner />
          <SecHead led="c">Transcript — Live Reconstruction</SecHead>
          <div className="lbl mb-2" style={{ fontSize:8 }}>INCOMING MESSAGE — WORD-LEVEL PROTECTION ANALYSIS</div>
          <div className="flex flex-wrap gap-2 mb-4">
          {transcriptWords.map(({ w, ok }) => (
              <div key={w} className="flex flex-col items-center gap-1">
                <span className={ok ? "badge-g" : "badge-r"} style={{ fontSize:10, padding:"2px 8px" }}>{w}</span>
                <span className="lbl" style={{ fontSize:7, color:ok?"var(--green)":"var(--red)" }}>
                  {ok ? "PROT" : "DEG"}
                </span>
              </div>
            ))}
          </div>
          <div className="lbl mb-2" style={{ fontSize:8 }}>BANDWIDTH PROTECTION PER WORD</div>
          <div className="w-full">
            <BandwidthChart />
          </div>
        </div>
      </div>
    </div>
  );
}

function AnalyticsView({ pipelineResult }) {
  const METRICS = [
    { label:"AVG SNR GAIN",     value:"+19.4 dB", color:"var(--cyan)",  sub:"vs baseline" },
    { label:"PACKET LOSS REDUCE", value:"73.2%",    color:"var(--green)", sub:"protected"   },
    { label:"LATENCY OVERHEAD",   value:"1.8 ms",   color:"var(--blue)",  sub:"acceptable"  },
    { label:"THREAT EVENTS",      value:"3",        color:"var(--red)",   sub:"last session" },
    { label:"ENCRYPTION CYCLES",   value:"4,812",    color:"var(--amber)", sub:"AES-256-GCM" },
    { label:"NODES ONLINE",       value:"7 / 8",    color:"var(--green)", sub:"Node E offline" },
  ];

  return (
    <div className="flex flex-col gap-3 overflow-auto flex-1" style={{ padding:"12px 16px" }}>
      <TelemetryGrid metrics={METRICS} />
     
     <TrajectoryChart data={SNR_DATA(pipelineResult)} />

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8 }}>
        <div className="card relative p-4" style={{ borderRadius:2 }}>
          <Corner />
          <SecHead led="c">Frequency Spectrum — Live</SecHead>
          <Spectrum />
          <div className="flex justify-between mt-1">
            {FREQ_LABELS.map(f => <span key={f} className="lbl" style={{ fontSize:6.5 }}>{f}</span>)}
          </div>
          <div className="flex items-center gap-4 mt-2">
            <div className="flex items-center gap-1.5">
              <div style={{ width:10, height:2, background:"var(--cyan)" }} />
              <span className="lbl" style={{ fontSize:7 }}>iTANTRA</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div style={{ width:10, height:2, background:"var(--blue)" }} />
              <span className="lbl" style={{ fontSize:7 }}>REFERENCE</span>
            </div>
          </div>
        </div>

        <div className="card relative p-4 flex flex-col" style={{ borderRadius:2 }}>
          <Corner />
          <SecHead led="g">System Event Log</SecHead>
          <div className="flex flex-col overflow-y-auto flex-1" style={{ maxHeight:200 }}>
            {EVENTS.map((ev, i) => (
              <div key={i} className="flex gap-2 items-start py-1.5" style={{ borderBottom:"1px solid var(--border-lo)", fontSize:9 }}>
                <span className="mono" style={{ color:"var(--lo)", flexShrink:0, fontSize:8 }}>{ev.ts}</span>
                <span className="raj font-bold px-1" style={{ color:ev.color, background:`${ev.color}15`, border:`1px solid ${ev.color}28`, fontSize:8, letterSpacing:".06em", flexShrink:0 }}>
                  {ev.type}
                </span>
                <span className="raj" style={{ color:"var(--mid)", fontSize:10, lineHeight:1.4 }}>{ev.msg}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card relative p-4 flex flex-col" style={{ borderRadius:2 }}>
          <Corner />
          <SecHead led="g">Active Relay Nodes</SecHead>
          <div className="flex flex-col flex-1">
            <div className="flex items-center py-1 border-b" style={{ borderColor:"var(--border)", fontSize:8 }}>
              <span className="lbl" style={{ width:32 }}>NODE</span>
              <span className="lbl" style={{ flex:1 }}>STATUS</span>
              <span className="lbl" style={{ width:48, textAlign:"right" }}>GAIN</span>
              <span className="lbl" style={{ width:40, textAlign:"right" }}>LOSS</span>
              <span className="lbl" style={{ width:36, textAlign:"right" }}>LAT</span>
            </div>
            {NODES.map(n => (
              <div key={n.id} className="flex items-center py-1.5 border-b" style={{ borderColor:"var(--border-lo)", fontSize:9 }}>
                <div className="flex items-center gap-1.5" style={{ width:32 }}>
                  <L c={n.led} />
                  <span className="mono font-bold" style={{ color:"var(--text)" }}>{n.id}</span>
                </div>
                <span className="raj font-bold" style={{ flex:1, fontSize:8, letterSpacing:".06em", color: n.status==="ONLINE"?"var(--green)":n.status==="DEGRADED"?"var(--amber)":"var(--red)" }}>
                  {n.status}
                </span>
                <span className="mono" style={{ width:48, textAlign:"right", color:"var(--cyan)" }}>{n.gain}</span>
                <span className="mono" style={{ width:40, textAlign:"right", color:"var(--mid)" }}>{n.loss}</span>
                <span className="mono" style={{ width:36, textAlign:"right", color:"var(--lo)" }}>{n.lat}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("live");
  const [mode, setMode] = useState("itantra");
  const [noise, setNoise] = useState(0.65);
   const [bitrate, setBitrate] = useState(3.5);
  const [selectedFile, setSelectedFile] = useState(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineResult, setPipelineResult] = useState(null);
  
  return (
    <div className="flex flex-col h-screen select-none" style={{ background: "var(--bg)", color: "var(--text)", fontFamily: "JetBrains Mono, monospace" }}>
      <Header tab={tab} setTab={setTab} />
      
      {/* Main Container with Sidebar Layout */}
      <main className="flex-1 flex overflow-hidden relative p-3 gap-3">
        <div className="flex-1 flex flex-col overflow-hidden">
        {tab === "live" && (
  <LiveView
    mode={mode}
    setMode={setMode}
    noise={noise}
    setNoise={setNoise}
    bitrate={bitrate}
    setBitrate={setBitrate}
    selectedFile={selectedFile}
    setSelectedFile={setSelectedFile}
    pipelineLoading={pipelineLoading}
    setPipelineLoading={setPipelineLoading}
    pipelineResult={pipelineResult}
    setPipelineResult={setPipelineResult}
  />
)}
         {tab === "analytics" && <AnalyticsView pipelineResult={pipelineResult} />}
        </div>
        
        {/* Right Speaker Sidebar */}
        <div className="flex-shrink-0 overflow-hidden h-full">
         <SpeakerSidebar pipelineResult={pipelineResult} />
        </div>
      </main>

      <footer className="flex items-center justify-between px-4 py-1 text-[9px] mono text-slate-500 border-t border-[#182030]" style={{ background: "var(--panel)" }}>
        <div className="flex items-center gap-4">
          <span>ENCRYPTION: AES-256-GCM</span>
          <span>PROTOCOL: iTANTRA-V2-SECURE</span>
          <span>LATENCY: 1.8ms</span>
        </div>
        <div>
          <span>SYSTEM STATUS: OPTIMAL // NODE-E RECONNECTING</span>
        </div>
      </footer>
    </div>
  );
}