import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

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

function L({ c, pulse }) {
  return <span className={`led led-${c}${pulse ? " pulse" : ""}`} />;
}

function SecHead({ led, children }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      {led && <L c={led} pulse={led==="c"||led==="g"} />}
      <span className="raj" style={{ fontSize:11, fontWeight:700, letterSpacing:".18em", textTransform:"uppercase", color:"var(--mid)" }}>{children}</span>
    </div>
  );
}

export default function TrajectoryChart({ data }) {
  return (
    <div className="card relative p-4" style={{ borderRadius:2 }}>
      <Corner />
     <SecHead led="c">Transmission Quality — iTantra vs Baseline</SecHead>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data} margin={{ top:4, right:12, left:0, bottom:0 }}>
          <defs>
            <linearGradient id="gradC" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#00C8FF" stopOpacity={0.22}/>
              <stop offset="95%" stopColor="#00C8FF" stopOpacity={0.02}/>
            </linearGradient>
            <linearGradient id="gradA" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#F59E0B" stopOpacity={0.18}/>
              <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.02}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 6" stroke="#182030" />
          <XAxis dataKey="t" tick={{ fill:"#4A6080", fontSize:9, fontFamily:"JetBrains Mono" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill:"#4A6080", fontSize:9, fontFamily:"JetBrains Mono" }} axisLine={false} tickLine={false} unit=" dB" />
          <Tooltip
            contentStyle={{ background:"#0D1422", border:"1px solid #24344D", fontFamily:"JetBrains Mono", fontSize:10 }}
            labelStyle={{ color:"#8B9AB2" }}
          />
          <Legend wrapperStyle={{ fontFamily:"Rajdhani", fontSize:10, letterSpacing:".1em", paddingTop:4 }} />
          <Area type="monotone" dataKey="itantra" name="iTANTRA" stroke="#00C8FF" strokeWidth={1.5} fill="url(#gradC)" dot={false} />
          <Area type="monotone" dataKey="baseline" name="BASELINE" stroke="#F59E0B" strokeWidth={1.5} fill="url(#gradA)" dot={false} strokeDasharray="4 3" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}