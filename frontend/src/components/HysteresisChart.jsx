import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceArea, ResponsiveContainer, Legend,
} from 'recharts'

export default function HysteresisChart({ data }) {
  if (!data) {
    return <div style={emptyStateStyle}>Run the hysteresis experiment to see the forward/reverse path.</div>
  }

  const { price_history, applied_sensitivity, pre_window, post_window } = data

  const chartData = price_history.map((price, i) => {
    const sensEntry = applied_sensitivity.find(([round]) => round === i)
    return {
      round: i,
      price,
      sensitivity: sensEntry ? sensEntry[1] : null,
    }
  })

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid stroke="var(--hairline)" strokeDasharray="2 4" />
          <XAxis
            dataKey="round" tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--dim)' }}
            stroke="var(--hairline)"
          />
          <YAxis
            yAxisId="price" tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--dim)' }}
            stroke="var(--hairline)" domain={['auto', 'auto']}
          />
          <YAxis
            yAxisId="sensitivity" orientation="right"
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--dim)' }}
            stroke="var(--hairline)"
          />
          <Tooltip
            contentStyle={{ background: 'var(--panel-raised)', border: '1px solid var(--hairline)', fontFamily: 'var(--font-mono)', fontSize: 12 }}
            labelStyle={{ color: 'var(--dim)' }}
          />
          <Legend wrapperStyle={{ fontFamily: 'var(--font-body)', fontSize: 12 }} />

          <ReferenceArea
            yAxisId="price" x1={pre_window[0]} x2={pre_window[1]}
            fill="var(--signal)" fillOpacity={0.06}
          />
          <ReferenceArea
            yAxisId="price" x1={post_window[0]} x2={post_window[1]}
            fill="var(--signal)" fillOpacity={0.06}
          />

          <Line
            yAxisId="price" type="monotone" dataKey="price" name="Price"
            stroke="var(--up)" dot={false} strokeWidth={1.5}
          />
          <Line
            yAxisId="sensitivity" type="monotone" dataKey="sensitivity" name="Trend-follower sensitivity"
            stroke="var(--signal)" dot={false} strokeWidth={1.5} strokeDasharray="4 3"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <div style={statsRowStyle}>
        <Stat label="pre-ramp mean price" value={`₹${data.pre_mean_price.toFixed(2)}`} />
        <Stat label="post-ramp mean price" value={`₹${data.post_mean_price.toFixed(2)}`} />
        <Stat label="price shift" value={`${data.price_shift_pct.toFixed(2)}%`} />
        <Stat label="volatility ratio (post/pre)" value={data.volatility_ratio.toFixed(2)} />
      </div>
      <p style={captionStyle}>
        Shaded bands mark the pre-ramp and post-reversal baseline windows used for comparison.
        A price shift near 0% and a volatility ratio near 1.0 indicate the market returned to its
        original equilibrium (no hysteresis detected in this run).
      </p>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div style={statStyle}>
      <div style={statValueStyle}>{value}</div>
      <div style={statLabelStyle}>{label}</div>
    </div>
  )
}

const statsRowStyle = {
  display: 'flex',
  gap: 24,
  marginTop: 12,
  flexWrap: 'wrap',
}

const statStyle = { minWidth: 120 }
const statValueStyle = { fontFamily: 'var(--font-mono)', fontSize: 18, color: 'var(--ink)' }
const statLabelStyle = { fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--dim)', marginTop: 2 }

const captionStyle = {
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  color: 'var(--dim)',
  marginTop: 12,
  lineHeight: 1.5,
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
