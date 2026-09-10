import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { colors, fonts, labelStyle } from '../theme.js'

// Shows, per word, how much "protection" the allocator gave it — the chart that
// visually proves the core USP: critical/uncertain words get protected, filler
// words degrade first. Styled to match the dashboard theme, not recharts defaults.
export default function ProtectionChart({ tokens, confidencePerToken, criticalityPerToken, protectionPerToken }) {
  if (!tokens || tokens.length === 0) {
    return (
      <div style={{ color: colors.textDim, fontFamily: fonts.mono, fontSize: '0.85rem' }}>
        Run the pipeline to see per-word protection.
      </div>
    )
  }

  const data = tokens.map((tok, i) => ({
    word: tok,
    protection: Math.round((protectionPerToken?.[i] ?? 0) * 100),
    confidence: Math.round((confidencePerToken?.[i] ?? 0) * 100),
    criticality: Math.round((criticalityPerToken?.[i] ?? 0) * 100),
  }))

  return (
    <div>
      <span style={labelStyle}>Bandwidth protection per word</span>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid stroke={colors.panelBorder} strokeDasharray="3 3" />
            <XAxis
              dataKey="word"
              tick={{ fill: colors.textDim, fontFamily: fonts.mono, fontSize: 11 }}
              axisLine={{ stroke: colors.panelBorder }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: colors.textDim, fontFamily: fonts.mono, fontSize: 11 }}
              axisLine={{ stroke: colors.panelBorder }}
              tickLine={false}
              label={{ value: '%', angle: -90, position: 'insideLeft', fill: colors.textDim }}
            />
            <Tooltip
              contentStyle={{ background: colors.panel, border: `1px solid ${colors.panelBorder}`, borderRadius: 6 }}
              labelStyle={{ color: colors.text, fontFamily: fonts.mono }}
              itemStyle={{ color: colors.accent, fontFamily: fonts.mono }}
            />
            <Bar dataKey="protection" fill={colors.accent} name="Bandwidth protection" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
