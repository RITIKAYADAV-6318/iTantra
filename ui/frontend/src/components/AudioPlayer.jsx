import { useMemo, useRef } from 'react'
import { colors, fonts, labelStyle } from '../theme.js'

// Takes the base64 audio string the backend returns and turns it into something
// the browser can actually play. Styled as a "transmission log" line — matches
// the theme without hiding that this is just an audio player.
// onPlayingChange (optional): lets a parent (e.g. TransmissionVisualizer) react
// to real play/pause state instead of guessing — the orb glow is driven by
// actual audio playback, not a decorative timer.
export default function AudioPlayer({ label, audioBase64, audioFormat = 'wav', accentColor, onPlayingChange }) {
  const audioRef = useRef(null)

  const audioUrl = useMemo(() => {
    if (!audioBase64) return null
    const byteChars = atob(audioBase64)
    const byteNumbers = new Array(byteChars.length)
    for (let i = 0; i < byteChars.length; i++) {
      byteNumbers[i] = byteChars.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray], { type: `audio/${audioFormat}` })
    return URL.createObjectURL(blob)
  }, [audioBase64, audioFormat])

  const dotColor = accentColor || colors.accent

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor, boxShadow: `0 0 6px ${dotColor}` }} />
        <span style={{ ...labelStyle, marginBottom: 0 }}>{label}</span>
      </div>
      {audioUrl ? (
        <audio
          ref={audioRef}
          controls
          src={audioUrl}
          style={{ width: '100%', height: '32px' }}
          onPlay={() => onPlayingChange?.(true)}
          onPause={() => onPlayingChange?.(false)}
          onEnded={() => onPlayingChange?.(false)}
        />
      ) : (
        <div style={{ fontFamily: fonts.mono, fontSize: '0.8rem', color: colors.textDim }}>
          No signal yet — waiting on pipeline output.
        </div>
      )}
    </div>
  )
}
