// Heat scale uses amber, deliberately distinct from the candle up/down
// colors (green/red) and the interactive-chrome accent (cyan) — so all
// three color roles stay visually unambiguous at a glance.
const HEAT_LOW = [19, 23, 32]   // matches --panel
const HEAT_HIGH = [242, 166, 90] // amber

function interpolateColor(t) {
  const [r1, g1, b1] = HEAT_LOW
  const [r2, g2, b2] = HEAT_HIGH
  const r = Math.round(r1 + (r2 - r1) * t)
  const g = Math.round(g1 + (g2 - g1) * t)
  const b = Math.round(b1 + (b2 - b1) * t)
  return `rgb(${r}, ${g}, ${b})`
}

export default function PhaseDiagramHeatmap({ data }) {
  if (!data) {
    return <div style={emptyStateStyle}>Run the phase diagram sweep to see the stability heatmap.</div>
  }

  const { trend_follower_counts, reaction_sensitivities, volatility_matrix } = data
  const flat = volatility_matrix.flat()
  const min = Math.min(...flat)
  const max = Math.max(...flat)
  const range = max - min || 1

  return (
    <div style={{ display: 'flex', gap: 8 }}>
      <div style={{ display: 'flex', flexDirection: 'column-reverse', gap: 2 }}>
        {trend_follower_counts.map((count) => (
          <div key={count} style={rowLabelStyle}>{count}</div>
        ))}
      </div>

      <div>
        <div style={{ display: 'flex', flexDirection: 'column-reverse', gap: 2 }}>
          {volatility_matrix.map((row, i) => (
            <div key={i} style={{ display: 'flex', gap: 2 }}>
              {row.map((value, j) => {
                const t = (value - min) / range
                return (
                  <div
                    key={j}
                    title={`trend-followers=${trend_follower_counts[i]}, sensitivity=${reaction_sensitivities[j]}: volatility=${value.toFixed(4)}`}
                    style={{
                      ...cellStyle,
                      background: interpolateColor(t),
                    }}
                  >
                    {value.toFixed(3)}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 2, marginTop: 4 }}>
          {reaction_sensitivities.map((s) => (
            <div key={s} style={colLabelStyle}>{s}</div>
          ))}
        </div>
        <div style={axisCaptionStyle}>reaction sensitivity →</div>
      </div>
    </div>
  )
}

const cellStyle = {
  width: 64,
  height: 40,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontFamily: 'var(--font-mono)',
  fontSize: 10,
  color: 'var(--void)',
  borderRadius: 3,
  cursor: 'default',
}

const rowLabelStyle = {
  width: 24,
  height: 40,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--dim)',
}

const colLabelStyle = {
  width: 64,
  textAlign: 'center',
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--dim)',
}

const axisCaptionStyle = {
  fontSize: 11,
  color: 'var(--dim)',
  marginTop: 4,
  fontFamily: 'var(--font-body)',
}

const emptyStateStyle = {
  height: 200,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--dim)',
  fontFamily: 'var(--font-body)',
  fontSize: 14,
  border: '1px dashed var(--hairline)',
  borderRadius: 8,
}
