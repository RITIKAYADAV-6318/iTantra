import React from "react";

function Corner({ accent = "var(--cyan-a20)" }) {
  return (
    <div className="absolute inset-0 pointer-events-none">
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 8,
          height: 8,
          borderTop: "1px solid " + accent,
          borderLeft: "1px solid " + accent,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: 8,
          height: 8,
          borderTop: "1px solid " + accent,
          borderRight: "1px solid " + accent,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: 8,
          height: 8,
          borderBottom: "1px solid " + accent,
          borderLeft: "1px solid " + accent,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: 8,
          height: 8,
          borderBottom: "1px solid " + accent,
          borderRight: "1px solid " + accent,
        }}
      />
    </div>
  );
}

export default function SpeakerSidebar({ pipelineResult }) {
  const events = (pipelineResult?.sound_event_tags || []).map(
    (tag, index) => ({
      type: String(tag).toUpperCase(),
      conf: "DETECTED",
      time: "LIVE",
      color: index % 2 === 0 ? "var(--cyan)" : "var(--amber)",
    })
  );

  return (
    <div
      className="flex flex-col h-full"
      style={{ minWidth: 280 }}
    >
      <div
        className="card relative flex flex-col h-full p-3"
        style={{
          borderRadius: 2,
          background: "var(--panel-dk)",
          border: "1px solid var(--border-lo)",
        }}
      >
        <Corner accent="var(--cyan-a20)" />

        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />

            <span
              className="lbl text-[9px] tracking-widest"
              style={{ color: "var(--cyan)" }}
            >
              SOUND-EVENT DETECTION
            </span>
          </div>

          <span
            className="mono text-[8px] px-1.5 py-0.5"
            style={{
              color: "var(--red)",
              background: "rgba(120,0,0,.25)",
              border: "1px solid var(--red)",
            }}
          >
            LIVE
          </span>
        </div>

        {/* Event List */}
        <div className="flex flex-col gap-2 overflow-y-auto pr-1 flex-1">
          {events.length > 0 ? (
            events.map((ev, index) => (
              <div
                key={index}
                className="p-2 flex items-center justify-between"
                style={{
                  background: "var(--panel)",
                  border: "1px solid var(--border-lo)",
                }}
              >
                <div>
                  <div
                    className="raj font-bold text-[10px] tracking-wider"
                    style={{ color: ev.color }}
                  >
                    [{ev.type}]
                  </div>

                  <div
                    className="mono text-[8px]"
                    style={{ color: "var(--mid)" }}
                  >
                    {ev.time}
                  </div>
                </div>

                <div
                  className="raj font-bold text-sm"
                  style={{ color: ev.color }}
                >
                  {ev.conf}
                </div>
              </div>
            ))
          ) : (
            /* Empty Detection State */
            <div className="flex-1 flex items-center justify-center">
              <div
                className="relative w-full p-7 text-center"
                style={{
                  background: "rgba(10,18,32,.75)",
                  border: "1px solid var(--border)",
                  boxShadow: "inset 0 0 18px rgba(0,200,255,.03)",
                }}
              >
                {/* Cyan Corner Brackets */}
                <div
                  style={{
                    position: "absolute",
                    top: -1,
                    left: -1,
                    width: 22,
                    height: 22,
                    borderTop: "2px solid var(--cyan)",
                    borderLeft: "2px solid var(--cyan)",
                  }}
                />

                <div
                  style={{
                    position: "absolute",
                    top: -1,
                    right: -1,
                    width: 22,
                    height: 22,
                    borderTop: "2px solid var(--cyan)",
                    borderRight: "2px solid var(--cyan)",
                  }}
                />

                <div
                  style={{
                    position: "absolute",
                    bottom: -1,
                    left: -1,
                    width: 22,
                    height: 22,
                    borderBottom: "2px solid var(--cyan)",
                    borderLeft: "2px solid var(--cyan)",
                  }}
                />

                <div
                  style={{
                    position: "absolute",
                    bottom: -1,
                    right: -1,
                    width: 22,
                    height: 22,
                    borderBottom: "2px solid var(--cyan)",
                    borderRight: "2px solid var(--cyan)",
                  }}
                />

                {/* Info Icon */}
                <div
                  className="mx-auto mb-3 flex items-center justify-center"
                  style={{
                    width: 28,
                    height: 28,
                    border: "2px solid var(--cyan)",
                    borderRadius: "50%",
                    color: "var(--cyan)",
                    fontSize: 16,
                    fontWeight: 700,
                    fontFamily: "monospace",
                    boxShadow: "0 0 8px var(--cyan-glow)",
                  }}
                >
                  i
                </div>

                <div
                  className="raj font-bold tracking-widest"
                  style={{
                    fontSize: 11,
                    color: "var(--cyan)",
                  }}
                >
                  NO SOUND EVENTS
                </div>

                <div
                  className="mono mt-2 tracking-wider"
                  style={{
                    fontSize: 8,
                    color: "var(--mid)",
                  }}
                >
                  AWAITING LIVE DETECTION
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}