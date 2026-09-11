import React from "react";

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

export default function TelemetryGrid({ metrics }) {
  return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:8 }}>
      {metrics.map(({ label, value, color, sub }) => (
        <div key={label} className="card relative p-3" style={{ borderRadius:2 }}>
          <Corner accent={color+"22"} />
          <div className="lbl" style={{ fontSize:8 }}>{label}</div>
          <div className="mono font-bold" style={{ fontSize:18, color, marginTop:4, marginBottom:2, letterSpacing:".02em" }}>{value}</div>
          <div className="lbl" style={{ fontSize:7 }}>{sub}</div>
        </div>
      ))}
    </div>
  );
}