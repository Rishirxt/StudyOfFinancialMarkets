import { useState } from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts'
import { runCircuitBreakerExperiment } from '../api.js'

export default function CircuitBreakerPanel() {
  const [params, setParams] = useState({
    fundamentalist_count: 8,
    trend_follower_count: 6,
    noise_count: 8,
    leveraged_count: 4,
    reaction_sensitivity: 1.6,
    num_rounds: 250,
    threshold_pct: 4.0,
    lookback: 5,
    halt_duration: 3,
    seed: 42,
  })

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  function update(key, val) {
    setParams(p => ({ ...p, [key]: val }))
  }

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      const res = await runCircuitBreakerExperiment(params)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? result.unprotected.price_history.map((unprotPrice, idx) => ({
    round: idx,
    unprotected: Number(unprotPrice.toFixed(2)),
    protected: result.protected.price_history[idx] !== undefined
      ? Number(result.protected.price_history[idx].toFixed(2))
      : null,
  })) : []

  return (
    <div style={panelContainerStyle}>
      <div style={headerStyle}>
        <div>
          <h2 style={titleStyle}>🛡️ Circuit Breaker Regulatory Halt Experiment</h2>
          <p style={subtitleStyle}>
            Tests whether trading halts (pausing agent orders for N rounds upon severe price drops)
            actually stabilize market equilibrium or merely delay price discovery.
          </p>
        </div>
        <button
          style={primaryBtnStyle}
          onClick={handleRun}
          disabled={loading}
          id="btn-run-cb-exp"
        >
          {loading ? 'Evaluating Halts…' : '🛡️ Run Circuit Breaker Experiment'}
        </button>
      </div>

      {error && <div style={errorBannerStyle}>{error}</div>}

      {/* Controls Grid */}
      <div style={gridStyle}>
        <div style={cardSectionStyle}>
          <div style={sectionTitleStyle}>⚡ Trigger Rules</div>
          <SliderRow
            label="Price Drop Threshold"
            value={params.threshold_pct}
            min={1.0}
            max={10.0}
            step={0.5}
            unit="%"
            onChange={v => update('threshold_pct', v)}
            color="var(--circuit)"
          />
          <SliderRow
            label="Lookback Window"
            value={params.lookback}
            min={2}
            max={15}
            unit=" rounds"
            onChange={v => update('lookback', v)}
          />
          <SliderRow
            label="Halt Duration"
            value={params.halt_duration}
            min={1}
            max={10}
            unit=" rounds"
            onChange={v => update('halt_duration', v)}
            color="var(--circuit)"
          />
        </div>

        <div style={cardSectionStyle}>
          <div style={sectionTitleStyle}>👥 Market Population & Volatility</div>
          <SliderRow
            label="Leveraged Traders"
            value={params.leveraged_count}
            min={0}
            max={10}
            onChange={v => update('leveraged_count', v)}
            color="var(--leveraged)"
          />
          <SliderRow
            label="Trend-Followers"
            value={params.trend_follower_count}
            min={2}
            max={12}
            onChange={v => update('trend_follower_count', v)}
            color="var(--trend-follower)"
          />
          <SliderRow
            label="Reaction Sensitivity"
            value={params.reaction_sensitivity}
            min={0.5}
            max={3.0}
            step={0.1}
            onChange={v => update('reaction_sensitivity', v)}
          />
        </div>

        <div style={cardSectionStyle}>
          <div style={sectionTitleStyle}>⏱️ Duration & Reproducibility</div>
          <SliderRow
            label="Rounds"
            value={params.num_rounds}
            min={100}
            max={400}
            step={25}
            onChange={v => update('num_rounds', v)}
          />
          <SliderRow
            label="Random Seed"
            value={params.seed}
            min={1}
            max={100}
            onChange={v => update('seed', v)}
          />
        </div>
      </div>

      {/* Result Metrics */}
      {result && (
        <div style={{ marginTop: 24 }}>
          <div style={metricsRowStyle}>
            <MetricCard
              label="Volatility Reduction"
              value={`${result.regulatory_effect.volatility_reduction_pct > 0 ? '-' : '+'}${Math.abs(result.regulatory_effect.volatility_reduction_pct).toFixed(1)}%`}
              sub={`Protected σ=${result.protected.metrics.volatility} vs Unprotected σ=${result.unprotected.metrics.volatility}`}
              color={result.regulatory_effect.volatility_reduction_pct > 0 ? 'var(--up)' : 'var(--down)'}
            />
            <MetricCard
              label="Drawdown Reduction"
              value={`${result.regulatory_effect.drawdown_reduction_pct > 0 ? '-' : '+'}${Math.abs(result.regulatory_effect.drawdown_reduction_pct).toFixed(1)}%`}
              sub={`Max DD: -${result.protected.metrics.max_drawdown_pct}% vs -${result.unprotected.metrics.max_drawdown_pct}%`}
              color={result.regulatory_effect.drawdown_reduction_pct > 0 ? 'var(--up)' : 'var(--down)'}
            />
            <MetricCard
              label="Halts Triggered"
              value={result.regulatory_effect.total_halts}
              sub={`${result.regulatory_effect.total_halts * params.halt_duration} rounds suspended`}
              color="var(--circuit)"
            />
            <MetricCard
              label="Final Price"
              value={`₹${result.protected.metrics.final_price.toFixed(2)}`}
              sub={`Unprotected ended at ₹${result.unprotected.metrics.final_price.toFixed(2)}`}
              color="var(--ink)"
            />
          </div>

          {/* Chart */}
          <div style={chartWrapperStyle}>
            <div style={chartHeaderStyle}>
              <span style={{ fontWeight: 600 }}>Unprotected Market (Red) vs Protected Market with Circuit Breaker (Green)</span>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData} margin={{ top: 12, right: 20, bottom: 8, left: 10 }}>
                <CartesianGrid stroke="var(--hairline)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="round"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 11, fill: 'var(--dim)' }}
                  stroke="var(--hairline)"
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 11, fill: 'var(--dim)' }}
                  stroke="var(--hairline)"
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--panel-raised)',
                    border: '1px solid var(--hairline)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="unprotected"
                  name="Unprotected Market"
                  stroke="var(--down)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="protected"
                  name="With Circuit Breaker"
                  stroke="var(--up)"
                  strokeWidth={2.5}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Events log of halts */}
          {result.protected.circuit_breaker?.halt_events?.length > 0 && (
            <div style={eventsBoxStyle}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--circuit)', marginBottom: 8 }}>
                ⚡ Halts Logged During Run:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {result.protected.circuit_breaker.halt_events.map((evt, i) => (
                  <div key={i} style={eventRowStyle}>
                    <span style={{ color: 'var(--dim)', minWidth: 70 }}>Round {evt.round}:</span>
                    <span>Triggered by <strong>{evt.pct_move}%</strong> drop at ₹{evt.trigger_price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={noteBoxStyle}>
            <strong>Regulatory Policy Insight:</strong> Exchange circuit breakers freeze trading to allow market participants to absorb panic and prevent margin cascades. However, if fundamental information or trend imbalance is unresolved, trading simply resumes its downward trajectory after the halt expires.
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, sub, color }) {
  return (
    <div style={metricCardStyle}>
      <div style={{ fontSize: 24, fontWeight: 700, fontFamily: 'var(--font-mono)', color: color || 'var(--ink)' }}>
        {value}
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-dim)', marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function SliderRow({ label, value, min, max, step = 1, unit = '', onChange, color }) {
  return (
    <div style={sliderRowStyle}>
      <div style={sliderLabelStyle}>
        <span style={{ color: color || 'var(--ink-dim)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={sliderInputStyle}
      />
    </div>
  )
}

const panelContainerStyle = {
  background: 'var(--panel)',
  borderRadius: 12,
  border: '1px solid var(--hairline)',
  padding: 24,
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  flexWrap: 'wrap',
  gap: 16,
}

const titleStyle = {
  margin: 0,
  fontSize: 20,
  fontWeight: 700,
  color: 'var(--ink)',
}

const subtitleStyle = {
  margin: '6px 0 0',
  fontSize: 13,
  color: 'var(--dim)',
  maxWidth: 750,
  lineHeight: 1.5,
}

const primaryBtnStyle = {
  background: 'var(--circuit)',
  color: '#000',
  fontWeight: 700,
  fontSize: 13,
  padding: '10px 18px',
  borderRadius: 8,
  border: 'none',
  cursor: 'pointer',
  transition: 'opacity 0.2s',
}

const errorBannerStyle = {
  padding: '10px 14px',
  borderRadius: 8,
  background: 'rgba(239, 68, 68, 0.1)',
  color: 'var(--down)',
  fontSize: 13,
  border: '1px solid rgba(239, 68, 68, 0.3)',
}

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
  gap: 16,
}

const cardSectionStyle = {
  background: 'var(--panel-raised)',
  border: '1px solid var(--hairline)',
  borderRadius: 8,
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const sectionTitleStyle = {
  fontSize: 12,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--dim)',
}

const sliderRowStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const sliderLabelStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: 12,
}

const sliderInputStyle = {
  width: '100%',
  cursor: 'pointer',
  accentColor: 'var(--signal)',
}

const metricsRowStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 12,
  marginBottom: 16,
}

const metricCardStyle = {
  background: 'var(--panel-raised)',
  border: '1px solid var(--hairline)',
  borderRadius: 8,
  padding: 16,
}

const chartWrapperStyle = {
  background: 'var(--panel-raised)',
  border: '1px solid var(--hairline)',
  borderRadius: 8,
  padding: 16,
}

const chartHeaderStyle = {
  fontSize: 13,
  color: 'var(--ink-dim)',
  marginBottom: 12,
}

const eventsBoxStyle = {
  marginTop: 16,
  padding: 14,
  borderRadius: 8,
  background: 'rgba(255, 255, 255, 0.02)',
  border: '1px solid var(--hairline)',
}

const eventRowStyle = {
  display: 'flex',
  fontSize: 12,
  color: 'var(--ink-dim)',
  gap: 8,
}

const noteBoxStyle = {
  marginTop: 16,
  padding: 12,
  borderRadius: 8,
  background: 'rgba(255, 255, 255, 0.03)',
  border: '1px solid var(--hairline)',
  fontSize: 12,
  color: 'var(--dim)',
  lineHeight: 1.6,
}
