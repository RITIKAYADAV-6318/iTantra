import { colors, fonts, labelStyle } from '../theme.js'

// The centerpiece visual: two orbs, "ORIGINAL MESSAGE" and "iTANTRA OUTPUT."
// Left glows while the before-audio is actually playing; right glows while the
// after-audio is actually playing. This is driven by real <audio> play/pause
// events (see AudioPlayer's onPlayingChange), not a timer or fake animation —
// if it's not playing, it's not glowing. That's the rule for everything on this
// dashboard, and it applies here too.
export default function TransmissionVisualizer({ senderPlaying, receiverPlaying, mode }) {
  const lineColor = mode === 'baseline' ? colors.danger : colors.accent

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '2rem',
        padding: '2rem 1rem',
      }}
    >
      <Orb active={senderPlaying} label="ORIGINAL MESSAGE" color={colors.text} />

      {/* Connecting channel — a traveling pulse only when something is actually
          transmitting, colored red for baseline (degrading) or cyan for iTantra
          (protected). */}
      <div style={{ flex: 1, maxWidth: 220, position: 'relative', height: 2 }}>
        <div style={{ width: '100%', height: 2, background: colors.panelBorder }} />
        {(senderPlaying || receiverPlaying) && (
          <div
            style={{
              position: 'absolute',
              top: -3,
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: lineColor,
              boxShadow: `0 0 10px ${lineColor}`,
              animation: 'itantra-pulse-travel 1.4s linear infinite',
            }}
          />
        )}
        <style>{`
          @keyframes itantra-pulse-travel {
            0% { left: 0%; opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { left: 96%; opacity: 0; }
          }
          @keyframes itantra-orb-glow {
            0%, 100% { box-shadow: 0 0 20px currentColor, 0 0 40px currentColor; transform: scale(1); }
            50% { box-shadow: 0 0 32px currentColor, 0 0 60px currentColor; transform: scale(1.05); }
          }
        `}</style>
      </div>

      <Orb
        active={receiverPlaying}
        label={mode === 'baseline' ? 'RECEIVED (DEGRADED)' : 'iTANTRA OUTPUT'}
        color={mode === 'baseline' ? colors.danger : colors.accent}
      />
    </div>
  )
}

function Orb({ active, label, color }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div
        style={{
          width: 90,
          height: 90,
          borderRadius: '50%',
          border: `2px solid ${active ? color : colors.panelBorder}`,
          background: active ? `radial-gradient(circle, ${color}33, transparent 70%)` : 'transparent',
          color: color,
          animation: active ? 'itantra-orb-glow 1.2s ease-in-out infinite' : 'none',
          transition: 'border-color 0.3s ease',
        }}
      />
      <div style={{ ...labelStyle, marginTop: '0.75rem', marginBottom: 0 }}>{label}</div>
    </div>
  )
}
