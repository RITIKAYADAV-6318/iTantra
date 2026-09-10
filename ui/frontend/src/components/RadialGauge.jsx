import { colors, fonts, labelStyle } from '../theme.js'

// A single, purposeful radial dial — showing the ONE number that matters most
// during the live demo (current channel bitrate). This replaces the reference
// image's decorative dials with a real, live readout.
export default function RadialGauge({ value, min = 0.5, max = 20, label = 'BITRATE', unit = 'kbps' }) {
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min)))
  const radius = 80
  const stroke = 10
  const normalizedRadius = radius - stroke / 2
  const circumference = normalizedRadius * 2 * Math.PI
  // Draw a 270-degree arc (leave a gap at the bottom) so it reads like a dial, not a full circle.
  const arcFraction = 0.75
  const dashArray = circumference * arcFraction
  const dashOffset = dashArray * (1 - pct)

  return (
    <div style={{ textAlign: 'center' }}>
      <span style={labelStyle}>{label}</span>
      <svg width={radius * 2} height={radius * 2} style={{ transform: 'rotate(135deg)' }}>
        {/* Track */}
        <circle
          cx={radius}
          cy={radius}
          r={normalizedRadius}
          fill="none"
          stroke={colors.panelBorder}
          strokeWidth={stroke}
          strokeDasharray={`${dashArray} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <circle
          cx={radius}
          cy={radius}
          r={normalizedRadius}
          fill="none"
          stroke={colors.accent}
          strokeWidth={stroke}
          strokeDasharray={`${dashArray} ${circumference}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{
            filter: `drop-shadow(0 0 6px ${colors.accent})`,
            transition: 'stroke-dashoffset 0.2s ease',
          }}
        />
      </svg>
      <div
        style={{
          marginTop: '-3.2rem',
          fontFamily: fonts.mono,
          fontWeight: 700,
          fontSize: '1.6rem',
          color: colors.text,
        }}
      >
        {value.toFixed(1)}
        <div style={{ fontSize: '0.7rem', color: colors.textDim, fontWeight: 400, letterSpacing: '0.05em' }}>
          {unit}
        </div>
      </div>
    </div>
  )
}
