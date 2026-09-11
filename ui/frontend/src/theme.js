// theme.js — single source of truth for the dashboard's look.
// Rule: every visual choice here exists to make the live demo easier to read at a
// glance from the back of a room, not to look busy. If a style addition doesn't
// serve legibility, it doesn't belong here.

export const colors = {
  bg: '#060b14',
  panel: '#0b1420',
  panelBorder: '#15384a',
  accent: '#2fd8ff',
  accentDim: '#155264',
  accentSoft: 'rgba(47, 216, 255, 0.12)',
  text: '#eaf6ff',
  textDim: '#7fa8bd',
  danger: '#ff5d5d',
  success: '#33e6a0',
  warning: '#ffb84d',
}

export const fonts = {
  mono: `'JetBrains Mono', 'Courier New', monospace`,
  sans: `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
}

// Reusable style objects — import these rather than re-writing glow/panel CSS
// in every component, so the look stays consistent everywhere.

export const panelStyle = {
  background: colors.panel,
  border: `1px solid ${colors.panelBorder}`,
  borderRadius: '12px',
  padding: '1.5rem',
  boxShadow: `0 0 24px rgba(47, 216, 255, 0.06), inset 0 0 40px rgba(47, 216, 255, 0.02)`,
}

export const glowText = {
  color: colors.accent,
  textShadow: `0 0 10px rgba(47, 216, 255, 0.55)`,
}

export const labelStyle = {
  fontFamily: fonts.sans,
  fontSize: '0.75rem',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: colors.textDim,
  marginBottom: '0.5rem',
  display: 'block',
}

export const bigNumberStyle = {
  fontFamily: fonts.mono,
  fontWeight: 700,
  fontSize: '2.25rem',
  color: colors.text,
  lineHeight: 1,
}
