import { colors, fonts, labelStyle } from '../theme.js'

// Control (drag to change bitrate). The RadialGauge component is the readout —
// this is the input. Keeping them separate: one shows, one controls, no confusion.
export default function BitrateSlider({ bitrate, onChange }) {
  return (
    <div>
      <span style={labelStyle}>Simulated channel bitrate</span>
      <input
        type="range"
        min="0.5"
        max="20"
        step="0.5"
        value={bitrate}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{
          width: '100%',
          accentColor: colors.accent,
        }}
      />
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: fonts.mono,
          fontSize: '0.7rem',
          color: colors.textDim,
          marginTop: '0.25rem',
        }}
      >
        <span>0.5 kbps — near-dead link</span>
        <span>20 kbps</span>
      </div>
    </div>
  )
}
