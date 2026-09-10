import { colors, fonts, labelStyle } from '../theme.js'

export default function ModeToggle({ mode, onChange }) {
  const baseBtn = {
    padding: '0.7rem 1.4rem',
    fontFamily: fonts.mono,
    fontSize: '0.85rem',
    letterSpacing: '0.05em',
    border: `1px solid ${colors.panelBorder}`,
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  }

  return (
    <div>
      <span style={labelStyle}>Mode</span>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          onClick={() => onChange('baseline')}
          style={{
            ...baseBtn,
            background: mode === 'baseline' ? colors.accentSoft : 'transparent',
            borderColor: mode === 'baseline' ? colors.danger : colors.panelBorder,
            color: mode === 'baseline' ? colors.danger : colors.textDim,
            boxShadow: mode === 'baseline' ? `0 0 10px rgba(255,93,93,0.25)` : 'none',
          }}
        >
          ● BASELINE (normal call)
        </button>
        <button
          onClick={() => onChange('itantra')}
          style={{
            ...baseBtn,
            background: mode === 'itantra' ? colors.accentSoft : 'transparent',
            borderColor: mode === 'itantra' ? colors.accent : colors.panelBorder,
            color: mode === 'itantra' ? colors.accent : colors.textDim,
            boxShadow: mode === 'itantra' ? `0 0 10px rgba(47,216,255,0.3)` : 'none',
          }}
        >
          ● iTANTRA MODE
        </button>
      </div>
    </div>
  )
}
