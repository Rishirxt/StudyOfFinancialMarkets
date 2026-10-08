import { useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { runHerdingExperiment } from '../api.js'

export default function HerdingExperimentPanel() {
  const [rounds, setRounds] = useState(500)
  const [seed, setSeed] = useState(42)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const resultConfig = result?.experiment_config
  const settingsChanged = resultConfig && (
    resultConfig.num_rounds !== rounds || resultConfig.seed !== seed
  )

  async function run() {
    setLoading(true)
    setError('')
    try {
      const requestConfig = { num_rounds: rounds, seed }
      const response = await runHerdingExperiment(requestConfig)
      setResult({
        ...response,
        // Older backend processes may not return experiment_config yet.
        experiment_config: response.experiment_config || requestConfig,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const series = result?.switching.strategy_history || []
  const chartData = series.map(item => ({
    round: item.round,
    Fundamentalists: item.fundamentalist,
    'Trend followers': item.trend_follower,
  }))

  return (
    <div style={pageStyle}>
      <header style={headerStyle}>
        <div>
          <h2 style={titleStyle}>Fixed mix vs. strategy switching</h2>
          <p style={subtitleStyle}>Agents switch between fundamentalist and trend-following rules based on recent marked-to-market strategy profitability. The experiment reports the observed results without assuming clustering will appear.</p>
        </div>
        <div style={controlsStyle}>
          <RangeControl label="Rounds" value={rounds} min={20} max={10000} step={20} onChange={setRounds} />
          <RangeControl label="Seed" value={seed} min={1} max={10000} step={1} onChange={setSeed} />
          <button style={runButtonStyle} onClick={run} disabled={loading}>
            {loading ? 'Running comparison…' : 'Run comparison'}
          </button>
        </div>
      </header>
      {error && <div style={errorStyle}>{error}</div>}
      {result && <div style={runInfoStyle}>
        {settingsChanged
          ? 'Settings changed. Run comparison to update the results.'
          : `Showing comparison for ${resultConfig?.num_rounds ?? rounds} rounds · seed ${resultConfig?.seed ?? seed}.`}
      </div>}
      {result && <>
        <div style={comparisonStyle}>
          <MetricGroup title="Fixed population" metrics={result.fixed} />
          <MetricGroup title="Performance switching" metrics={result.switching} />
        </div>
        <section style={panelStyle}>
          <h3 style={sectionTitle}>Switching population by round</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 10, right: 18, bottom: 8, left: 4 }}>
                <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" />
                <XAxis dataKey="round" stroke="var(--dim)" />
                <YAxis allowDecimals={false} stroke="var(--dim)" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="Fundamentalists" stroke="var(--fundamentalist)" dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="Trend followers" stroke="var(--trend-follower)" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div style={switchSummary}>
            {series.length ? `Cumulative strategy switches: ${series[series.length - 1].cumulative_switches}` : 'No switchable agents configured.'}
          </div>
        </section>
      </>}
    </div>
  )
}

function MetricGroup({ title, metrics }) {
  return (
    <section style={panelStyle}>
      <h3 style={sectionTitle}>{title}</h3>
      <div style={metricGrid}>
        <Metric label="Return volatility" value={metrics.volatility.toFixed(5)} />
        <Metric label="Excess kurtosis" value={metrics.excess_kurtosis == null ? 'n/a' : metrics.excess_kurtosis.toFixed(3)} />
        <Metric label="Lag 1 raw return ACF" value={metrics.raw_return_autocorrelation[0]?.toFixed(3) ?? 'n/a'} />
        <Metric label="Lag 1 squared return ACF" value={metrics.squared_return_autocorrelation[0]?.toFixed(3) ?? 'n/a'} />
        <Metric label="Lag 1 absolute return ACF" value={metrics.absolute_return_autocorrelation[0]?.toFixed(3) ?? 'n/a'} />
      </div>
      <p style={noteStyle}>Approximate 95% ACF reference band: ±{metrics.significance_band.toFixed(3)}</p>
    </section>
  )
}

function Metric({ label, value }) {
  return <div><div style={metricValue}>{value}</div><div style={metricLabel}>{label}</div></div>
}

function RangeControl({ label, value, min, max, step, onChange }) {
  return (
    <label style={controlStyle}>
      <span style={controlLabelStyle}>{label}</span>
      <span style={controlValueStyle}>{value}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={event => onChange(Number(event.target.value))}
        style={rangeStyle}
      />
    </label>
  )
}

const pageStyle = { display: 'grid', gap: 16 }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: 16, flexWrap: 'wrap' }
const titleStyle = { margin: 0, color: 'var(--ink-bright)', fontSize: 20 }
const subtitleStyle = { maxWidth: 760, margin: '6px 0 0', color: 'var(--ink-dim)', fontSize: 12 }
const controlsStyle = { display: 'flex', alignItems: 'end', gap: 14, flexWrap: 'wrap', color: 'var(--ink-dim)', fontSize: 11 }
const controlStyle = { display: 'grid', gridTemplateColumns: 'auto auto', alignItems: 'center', gap: '2px 10px', minWidth: 135 }
const controlLabelStyle = { color: 'var(--ink-dim)' }
const controlValueStyle = { justifySelf: 'end', color: 'var(--ink-bright)', fontFamily: 'var(--font-mono)', fontWeight: 700 }
const rangeStyle = { gridColumn: '1 / -1', width: '100%', accentColor: 'var(--signal)', cursor: 'pointer' }
const runButtonStyle = { background: 'var(--signal)', color: '#fff', fontWeight: 700, padding: '10px 16px', border: 0, borderRadius: 7, cursor: 'pointer' }
const comparisonStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }
const panelStyle = { background: 'var(--panel)', border: '1px solid var(--hairline)', borderRadius: 12, padding: 18 }
const sectionTitle = { margin: '0 0 14px', color: 'var(--ink-bright)', fontSize: 14 }
const metricGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', gap: 14 }
const metricValue = { color: 'var(--signal-bright)', fontFamily: 'var(--font-mono)', fontSize: 17, fontWeight: 700 }
const metricLabel = { color: 'var(--dim)', fontSize: 10, marginTop: 3 }
const noteStyle = { margin: '14px 0 0', color: 'var(--dim)', fontSize: 11 }
const switchSummary = { marginTop: 10, color: 'var(--ink-dim)', fontSize: 11 }
const errorStyle = { color: 'var(--down)', padding: 10, border: '1px solid var(--down)', borderRadius: 6 }
const runInfoStyle = { color: 'var(--ink-dim)', fontSize: 11, padding: '8px 10px', background: 'var(--panel)', border: '1px solid var(--hairline)', borderRadius: 7 }
