import { useState } from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts'
import { runLeverageExperiment } from '../api.js'

export default function LeverageExperimentPanel() {
  const [params, setParams] = useState({
    fundamentalist_count: 8,
    trend_follower_count: 4,
    noise_count: 8,
    leveraged_count: 6,
    leverage_ratio: 3.0,
    margin_call_threshold: 0.3,
    reaction_sensitivity: 1.4,
    num_rounds: 250,
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
      const res = await runLeverageExperiment(params)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? result.baseline.price_history.map((basePrice, idx) => ({
    round: idx,
    baseline: Number(basePrice.toFixed(2)),
    leveraged: result.leveraged.price_history[idx] !== undefined
      ? Number(result.leveraged.price_history[idx].toFixed(2))
      : null,
  })) : []

  return (
    <div style={panelContainerStyle}>
      <div style={headerStyle}>
        <div>
          <h2 style={titleStyle}>⚡ Leverage & Cascading Liquidation Experiment</h2>
          <p style={subtitleStyle}>
            Compares un-leveraged baseline trading against leveraged trend-followers subject to forced margin call liquidations.
            Tests whether margin spirals act as a crash amplifier creating lasting market scarring.
          </p>
        </div>
        <button
          style={primaryBtnStyle}
          onClick={handleRun}
          disabled={loading}
          id="btn-run-leverage-exp"
        >
          {loading ? 'Simulating Spirals…' : '⚡ Run Leverage Experiment'}
        </button>
      </div>

      {error && <div style={errorBannerStyle}>{error}</div>}

      {/* Controls Grid */}
      <div style={gridStyle}>
        <div style={cardSectionStyle}>
          <div style={sectionTitleStyle}>👥 Agent Counts</div>
          <SliderRow
            label="Leveraged Traders"
            value={params.leveraged_count}
            min={1}
            max={12}
            onChange={v => update('leveraged_count', v)}
            color="var(--leveraged)"
          />
          <SliderRow
            label="Unleveraged Trend Followers"
            value={params.trend_follower_count}
            min={0}
            max={12}
            onChange={v => update('trend_follower_count', v)}
            color="var(--trend-follower)"
          />
          <SliderRow
            label="Fundamentalists"
            value={params.fundamentalist_count}
            min={2}
            max={16}
            onChange={v => update('fundamentalist_count', v)}
            color="var(--fundamentalist)"
          />
        </div>

        <div style={cardSectionStyle}>
          <div style={sectionTitleStyle}>⚙️ Leverage & Margin Rules</div>
          <SliderRow
            label="Leverage Ratio"
            value={params.leverage_ratio}
            min={1.0}
            max={6.0}
            step={0.5}
            unit="x"
            onChange={v => update('leverage_ratio', v)}
            color="var(--leverage)"
          />
          <SliderRow
            label="Margin Call Threshold"
            value={Math.round(params.margin_call_threshold * 100)}
            min={10}
            max={60}
            unit="%"
            onChange={v => update('margin_call_threshold', v / 100)}
            color="var(--down)"
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
              label="Volatility Amplification"
              value={`${result.cascade_amplification.volatility_ratio.toFixed(2)}x`}
              sub="Leveraged vs Baseline std-dev"
              color={result.cascade_amplification.volatility_ratio > 1.2 ? 'var(--down)' : 'var(--up)'}
            />
            <MetricCard
              label="Drawdown Amplification"
              value={`${result.cascade_amplification.drawdown_ratio.toFixed(2)}x`}
              sub={`Peak drop: -${result.leveraged.metrics.max_drawdown_pct}% vs -${result.baseline.metrics.max_drawdown_pct}%`}
              color={result.cascade_amplification.drawdown_ratio > 1.2 ? 'var(--down)' : 'var(--up)'}
            />
            <MetricCard
              label="Forced Liquidations"
              value={result.cascade_amplification.margin_calls_triggered}
              sub="Emergency market dump orders"
              color={result.cascade_amplification.margin_calls_triggered > 0 ? 'var(--down)' : 'var(--ink-dim)'}
            />
            <MetricCard
              label="Final Price Impact"
              value={`₹${result.leveraged.metrics.final_price.toFixed(2)}`}
              sub={`Baseline closed at ₹${result.baseline.metrics.final_price.toFixed(2)}`}
              color="var(--ink)"
            />
          </div>

          {/* Chart */}
          <div style={chartWrapperStyle}>
            <div style={chartHeaderStyle}>
              <span style={{ fontWeight: 600 }}>Price Trajectory: Baseline (Blue) vs Leveraged Spiral (Orange)</span>
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
                  dataKey="baseline"
                  name="Un-leveraged Baseline"
                  stroke="var(--signal)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="leveraged"
                  name="Leveraged (Margin Calls)"
                  stroke="var(--down)"
                  strokeWidth={2.5}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Explanatory note */}
          <div style={noteBoxStyle}>
            <strong>Scientific Context:</strong> When leveraged agents face losses, their equity shrinks faster than their portfolio size. Once equity breaches {Math.round(params.margin_call_threshold * 100)}%, they execute forced liquidation sell orders regardless of momentum signal. In a thin book, this depresses the price further, causing sibling leveraged agents to breach margin thresholds — producing 2008-style endogenous cascades.
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
  background: 'var(--leverage)',
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
