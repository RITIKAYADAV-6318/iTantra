import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import BitrateSlider from './components/BitrateSlider.jsx'
import ModeToggle from './components/ModeToggle.jsx'
import ProtectionChart from './components/ProtectionChart.jsx'
import AudioPlayer from './components/AudioPlayer.jsx'
import RadialGauge from './components/RadialGauge.jsx'
import TransmissionVisualizer from './components/TransmissionVisualizer.jsx'
import { runPipeline } from './api.js'
import { colors, fonts, panelStyle, glowText, labelStyle, bigNumberStyle } from './theme.js'

// NODE CONCEPT — see docs/SCREEN_ARCHITECTURE.md. Open with ?node=A or ?node=B.
const params = new URLSearchParams(window.location.search)
const nodeLabel = params.get('node') || 'A'

// SCREEN CONCEPT — 2 screens, not more (see docs/SCREEN_ARCHITECTURE.md):
// "live"      — what's on screen during the actual live demo. Calm, minimal, one
//               primary action. This is what judges watch during the core moment.
// "analytics" — shown after the live moment, during explanation/Q&A. Denser is
//               fine here since nobody's watching a live "wow" beat on this tab.

const tabs = [
  { id: 'live', label: 'LIVE TRANSMISSION' },
  { id: 'analytics', label: 'ANALYTICS' },
]

export default function App() {
  const [tab, setTab] = useState('live')
  const [bitrate, setBitrate] = useState(5.0)
  const [noise, setNoise] = useState(0.3)
  const [mode, setMode] = useState('itantra')
  const [result, setResult] = useState(null)
  const [beforeAudio, setBeforeAudio] = useState(null)
  const [afterAudio, setAfterAudio] = useState(null)
  const [senderPlaying, setSenderPlaying] = useState(false)
  const [receiverPlaying, setReceiverPlaying] = useState(false)
  const [runHistory, setRunHistory] = useState([]) // for the Analytics tab
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      const data = await runPipeline({ bitrateKbps: bitrate, noiseLevel: noise, mode })
      setResult(data)
      if (data.mode === 'baseline') {
        setBeforeAudio(data)
      } else {
        setAfterAudio(data)
      }
      setRunHistory((prev) => [
        ...prev,
        { run: prev.length + 1, packetBytes: data.packet_bytes, mode: data.mode, bitrate },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: colors.bg,
        fontFamily: fonts.sans,
        color: colors.text,
        padding: '2rem',
      }}
    >
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>

        {/* HEADER */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.5rem',
            paddingBottom: '1rem',
            borderBottom: `1px solid ${colors.panelBorder}`,
          }}
        >
          <div>
            <div style={{ ...glowText, fontFamily: fonts.mono, fontSize: '1.6rem', fontWeight: 700 }}>
              iTANTRA
            </div>
            <div style={{ color: colors.textDim, fontSize: '0.85rem', marginTop: '0.15rem' }}>
              "We don't just protect the connection — we protect the words that matter most."
            </div>
          </div>
          <div
            style={{
              ...panelStyle,
              padding: '0.5rem 1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
            }}
          >
            <span
              style={{
                width: 8, height: 8, borderRadius: '50%',
                background: colors.success, boxShadow: `0 0 6px ${colors.success}`,
              }}
            />
            <span style={{ fontFamily: fonts.mono, fontSize: '0.85rem', letterSpacing: '0.05em' }}>
              NODE {nodeLabel}
            </span>
          </div>
        </div>

        {/* TAB NAV — 2 screens only. Simple, low-risk to click mid-pitch. */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: '0.5rem 1rem',
                fontFamily: fonts.mono,
                fontSize: '0.8rem',
                letterSpacing: '0.05em',
                background: tab === t.id ? colors.accentSoft : 'transparent',
                color: tab === t.id ? colors.accent : colors.textDim,
                border: `1px solid ${tab === t.id ? colors.accent : colors.panelBorder}`,
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'live' && (
          <>
            {/* CONTROLS */}
            <div style={{ ...panelStyle, marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <ModeToggle mode={mode} onChange={setMode} />
                <RadialGauge value={bitrate} label="BITRATE" unit="kbps" />
                <div style={{ flex: 1, minWidth: 220 }}>
                  <BitrateSlider bitrate={bitrate} onChange={setBitrate} />
                  <div style={{ marginTop: '1rem' }}>
                    <span style={labelStyle}>Channel noise: {(noise * 100).toFixed(0)}%</span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={noise}
                      onChange={(e) => setNoise(parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: colors.accent }}
                    />
                  </div>
                </div>
              </div>

              <button
                onClick={handleRun}
                disabled={loading}
                style={{
                  marginTop: '1.5rem',
                  width: '100%',
                  padding: '0.9rem',
                  fontFamily: fonts.mono,
                  fontSize: '0.9rem',
                  letterSpacing: '0.08em',
                  fontWeight: 700,
                  background: loading ? colors.accentDim : colors.accent,
                  color: colors.bg,
                  border: 'none',
                  borderRadius: '8px',
                  cursor: loading ? 'default' : 'pointer',
                  boxShadow: loading ? 'none' : `0 0 20px rgba(47,216,255,0.35)`,
                  transition: 'all 0.15s ease',
                }}
              >
                {loading ? 'TRANSMITTING...' : '▶ RUN DEMO SENTENCE'}
              </button>

              {error && (
                <p style={{ color: colors.danger, marginTop: '1rem', fontFamily: fonts.mono, fontSize: '0.85rem' }}>
                  {error}
                </p>
              )}
            </div>

            {/* TWO-ORB VISUALIZER — glows only while audio is actually playing */}
            {(beforeAudio || afterAudio) && (
              <div style={{ ...panelStyle, marginBottom: '1.5rem' }}>
                <TransmissionVisualizer
                  senderPlaying={senderPlaying}
                  receiverPlaying={receiverPlaying}
                  mode={mode}
                />
              </div>
            )}

            {/* STATUS ROW */}
            {result && (
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ ...panelStyle, flex: 1, padding: '1rem' }}>
                  <span style={labelStyle}>Language</span>
                  <div style={bigNumberStyle}>{result.language.toUpperCase()}</div>
                </div>
                <div style={{ ...panelStyle, flex: 1, padding: '1rem' }}>
                  <span style={labelStyle}>Mode</span>
                  <div style={{ ...bigNumberStyle, fontSize: '1.4rem', color: result.mode === 'itantra' ? colors.accent : colors.danger }}>
                    {result.mode === 'itantra' ? 'iTANTRA' : 'BASELINE'}
                  </div>
                </div>
                <div style={{ ...panelStyle, flex: 1, padding: '1rem' }}>
                  <span style={labelStyle}>Packet size</span>
                  <div style={bigNumberStyle}>{result.packet_bytes}<span style={{ fontSize: '1rem', color: colors.textDim }}> B</span></div>
                </div>
              </div>
            )}

            {/* TRANSCRIBED TEXT */}
            {result && (
              <div style={{ ...panelStyle, marginBottom: '1.5rem' }}>
                <span style={labelStyle}>Transcribed / reconstructed text</span>
                <div style={{ fontFamily: fonts.mono, fontSize: '1.1rem', color: colors.text }}>
                  "{result.text}"
                </div>
              </div>
            )}

            {/* BEFORE / AFTER AUDIO — drives the orb visualizer above */}
            {(beforeAudio || afterAudio) && (
              <div style={{ ...panelStyle, marginBottom: '1.5rem' }}>
                <span style={labelStyle}>Transmission log — listen to the difference</span>
                <AudioPlayer
                  label="BEFORE — normal call, no protection"
                  audioBase64={beforeAudio?.audio_base64}
                  audioFormat={beforeAudio?.audio_format}
                  accentColor={colors.danger}
                  onPlayingChange={setSenderPlaying}
                />
                <AudioPlayer
                  label="AFTER — iTantra mode"
                  audioBase64={afterAudio?.audio_base64}
                  audioFormat={afterAudio?.audio_format}
                  accentColor={colors.accent}
                  onPlayingChange={setReceiverPlaying}
                />
              </div>
            )}

            {/* PROTECTION CHART */}
            {result && (
              <div style={panelStyle}>
                <ProtectionChart
                  tokens={result.text.split(' ')}
                  confidencePerToken={result.confidence_per_token}
                  criticalityPerToken={result.criticality_per_token}
                  protectionPerToken={result.protection_per_token}
                />
              </div>
            )}
          </>
        )}

        {tab === 'analytics' && (
          <>
            <div style={{ ...panelStyle, marginBottom: '1.5rem' }}>
              <span style={labelStyle}>Packet size across runs (this session)</span>
              {runHistory.length > 0 ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <LineChart data={runHistory}>
                      <CartesianGrid stroke={colors.panelBorder} strokeDasharray="3 3" />
                      <XAxis dataKey="run" tick={{ fill: colors.textDim, fontFamily: fonts.mono, fontSize: 11 }} />
                      <YAxis tick={{ fill: colors.textDim, fontFamily: fonts.mono, fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: colors.panel, border: `1px solid ${colors.panelBorder}` }}
                        labelStyle={{ color: colors.text, fontFamily: fonts.mono }}
                      />
                      <Line type="monotone" dataKey="packetBytes" stroke={colors.accent} strokeWidth={2} dot={{ fill: colors.accent }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ color: colors.textDim, fontFamily: fonts.mono, fontSize: '0.85rem' }}>
                  Run the pipeline on the Live tab to build up history here.
                </div>
              )}
            </div>

            <div style={{ ...panelStyle, marginBottom: '1.5rem' }}>
              <span style={labelStyle}>Run log</span>
              {runHistory.length > 0 ? (
                <table style={{ width: '100%', fontFamily: fonts.mono, fontSize: '0.85rem', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ color: colors.textDim, textAlign: 'left' }}>
                      <th style={{ padding: '0.4rem 0' }}>#</th>
                      <th>Mode</th>
                      <th>Bitrate (kbps)</th>
                      <th>Packet size (B)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runHistory.map((r) => (
                      <tr key={r.run} style={{ borderTop: `1px solid ${colors.panelBorder}` }}>
                        <td style={{ padding: '0.4rem 0' }}>{r.run}</td>
                        <td style={{ color: r.mode === 'itantra' ? colors.accent : colors.danger }}>{r.mode}</td>
                        <td>{r.bitrate.toFixed(1)}</td>
                        <td>{r.packetBytes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: colors.textDim, fontFamily: fonts.mono, fontSize: '0.85rem' }}>
                  No runs yet.
                </div>
              )}
            </div>

            <div style={{ ...panelStyle }}>
              <span style={labelStyle}>WER / QIEA benchmark</span>
              <div style={{ color: colors.textDim, fontFamily: fonts.mono, fontSize: '0.85rem' }}>
                Full WER table and QIEA-vs-greedy benchmark chart live in the pitch deck
                (docs/BUILD_PLAN.md, Day 4) — pulled up separately during the numbers
                segment of the pitch, not rebuilt here to avoid duplicating work under
                the deadline.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
