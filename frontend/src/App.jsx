import { useState } from 'react'
import CandlestickChart from './components/CandlestickChart.jsx'
import PhaseDiagramHeatmap from './components/PhaseDiagramHeatmap.jsx'
import HysteresisChart from './components/HysteresisChart.jsx'
import { runSimulation, runPhaseDiagram, runHysteresis } from './api.js'

export default function App() {
  const [params, setParams] = useState({
    fundamentalist_count: 8,
    trend_follower_count: 6,
    noise_count: 8,
    reaction_sensitivity: 1.2,
    num_rounds: 300,
    seed: 42,
  })

  const [simResult, setSimResult] = useState(null)
  const [simLoading, setSimLoading] = useState(false)
  const [simError, setSimError] = useState(null)

  const [phaseResult, setPhaseResult] = useState(null)
  const [phaseLoading, setPhaseLoading] = useState(false)

  const [hysteresisResult, setHysteresisResult] = useState(null)
  const [hysteresisLoading, setHysteresisLoading] = useState(false)

  async function handleRunSimulation() {
    setSimLoading(true)
    setSimError(null)
    try {
      const result = await runSimulation(params)
      setSimResult(result)
    } catch (err) {
      setSimError(err.message)
    } finally {
      setSimLoading(false)
    }
  }

  async function handleRunPhaseDiagram() {
    setPhaseLoading(true)
    try {
      const result = await runPhaseDiagram({})
      setPhaseResult(result)
    } finally {
      setPhaseLoading(false)
    }
  }

  async function handleRunHysteresis() {
    setHysteresisLoading(true)
    try {
      const result = await runHysteresis({})
      setHysteresisResult(result)
    } finally {
      setHysteresisLoading(false)
    }
  }

  function updateParam(key, value) {
    setParams((p) => ({ ...p, [key]: value }))
  }

  return (
    <div style={pageStyle}>
      <header style={headerStyle}>
        <div>
          <div style={eyebrowStyle}>AGENT-BASED MARKET SIMULATION</div>
          <h1 style={titleStyle}>Market Sim // Control Deck</h1>
        </div>
      </header>

      <section style={panelStyle}>
        <h2 style={panelTitleStyle}>Population &amp; run controls</h2>
        <div style={controlsGridStyle}>
          <SliderControl
            label="Fundamentalists" value={params.fundamentalist_count}
            min={0} max={20} onChange={(v) => updateParam('fundamentalist_count', v)}
          />
          <SliderControl
            label="Trend-followers" value={params.trend_follower_count}
            min={0} max={20} onChange={(v) => updateParam('trend_follower_count', v)}
          />
          <SliderControl
            label="Noise traders" value={params.noise_count}
            min={0} max={20} onChange={(v) => updateParam('noise_count', v)}
          />
          <SliderControl
            label="Reaction sensitivity" value={params.reaction_sensitivity}
            min={0.1} max={4} step={0.1} onChange={(v) => updateParam('reaction_sensitivity', v)}
          />
          <SliderControl
            label="Rounds" value={params.num_rounds}
            min={50} max={1000} step={50} onChange={(v) => updateParam('num_rounds', v)}
          />
        </div>
        <button style={primaryButtonStyle} onClick={handleRunSimulation} disabled={simLoading}>
          {simLoading ? 'Running…' : 'Run simulation'}
        </button>
        {simError && <div style={errorStyle}>{simError}. Is the backend running on localhost:8000?</div>}
      </section>

      <div style={mainGridStyle}>
        <section style={panelStyle}>
          <h2 style={panelTitleStyle}>Price action</h2>
          <CandlestickChart candles={simResult?.candles} />
        </section>

        <section style={panelStyle}>
          <h2 style={panelTitleStyle}>Run summary</h2>
          {simResult ? (
            <div style={statsColumnStyle}>
              <Stat label="final price" value={simResult.final_price.toFixed(2)} />
              <Stat label="total trades" value={simResult.total_trades} />
              <Stat label="candles" value={simResult.candles.length} />
              <Stat
                label="best bid / ask"
                value={
                  simResult.order_book_snapshot?.bids?.[0]
                    ? `${simResult.order_book_snapshot.bids[0].price.toFixed(2)} / ${simResult.order_book_snapshot.asks[0]?.price.toFixed(2) ?? '—'}`
                    : '—'
                }
              />
            </div>
          ) : (
            <div style={{ color: 'var(--dim)', fontSize: 13 }}>Run a simulation to see summary stats.</div>
          )}
        </section>
      </div>

      <div style={mainGridStyle}>
        <section style={panelStyle}>
          <h2 style={panelTitleStyle}>Phase diagram</h2>
          <p style={panelSubtitleStyle}>
            Sweeps trend-follower count × reaction sensitivity, showing where the market transitions
            from stable to unstable.
          </p>
          <button style={secondaryButtonStyle} onClick={handleRunPhaseDiagram} disabled={phaseLoading}>
            {phaseLoading ? 'Sweeping…' : 'Run phase diagram sweep'}
          </button>
          <div style={{ marginTop: 16 }}>
            <PhaseDiagramHeatmap data={phaseResult} />
          </div>
        </section>

        <section style={panelStyle}>
          <h2 style={panelTitleStyle}>Hysteresis experiment</h2>
          <p style={panelSubtitleStyle}>
            Ramps trend-follower sensitivity up past the instability threshold, then back down —
            testing whether the market returns to its original equilibrium.
          </p>
          <button style={secondaryButtonStyle} onClick={handleRunHysteresis} disabled={hysteresisLoading}>
            {hysteresisLoading ? 'Running experiment…' : 'Run hysteresis experiment'}
          </button>
          <div style={{ marginTop: 16 }}>
            <HysteresisChart data={hysteresisResult} />
          </div>
        </section>
      </div>
    </div>
  )
}

function SliderControl({ label, value, min, max, step = 1, onChange }) {
  return (
    <label style={sliderWrapStyle}>
      <div style={sliderLabelRowStyle}>
        <span>{label}</span>
        <span style={sliderValueStyle}>{value}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={sliderInputStyle}
      />
    </label>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, color: 'var(--ink)' }}>{value}</div>
      <div style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--dim)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

/* --- styles --- */

const pageStyle = {
  maxWidth: 1200,
  margin: '0 auto',
  padding: '32px 24px 64px',
}

const headerStyle = {
  marginBottom: 24,
}

const eyebrowStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  letterSpacing: '0.08em',
  color: 'var(--signal)',
  marginBottom: 4,
}

const titleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: 28,
  fontWeight: 600,
  margin: 0,
  color: 'var(--ink)',
}

const panelStyle = {
  background: 'var(--panel)',
  border: '1px solid var(--hairline)',
  borderRadius: 10,
  padding: 20,
  marginBottom: 20,
}

const panelTitleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: 16,
  fontWeight: 600,
  margin: '0 0 12px',
  color: 'var(--ink)',
}

const panelSubtitleStyle = {
  fontFamily: 'var(--font-body)',
  fontSize: 12.5,
  color: 'var(--dim)',
  marginTop: -6,
  marginBottom: 14,
  lineHeight: 1.5,
}

const controlsGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 16,
  marginBottom: 16,
}

const sliderWrapStyle = { display: 'block' }

const sliderLabelRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  color: 'var(--dim)',
  marginBottom: 6,
}

const sliderValueStyle = {
  fontFamily: 'var(--font-mono)',
  color: 'var(--signal)',
}

const sliderInputStyle = {
  width: '100%',
  accentColor: '#4FC3E0',
}

const primaryButtonStyle = {
  background: 'var(--signal)',
  color: 'var(--void)',
  border: 'none',
  borderRadius: 6,
  padding: '10px 20px',
  fontSize: 13,
  fontWeight: 600,
  fontFamily: 'var(--font-body)',
}

const secondaryButtonStyle = {
  background: 'transparent',
  color: 'var(--signal)',
  border: '1px solid var(--signal-dim)',
  borderRadius: 6,
  padding: '9px 18px',
  fontSize: 13,
  fontWeight: 500,
  fontFamily: 'var(--font-body)',
}

const errorStyle = {
  marginTop: 12,
  color: 'var(--down)',
  fontSize: 12.5,
  fontFamily: 'var(--font-body)',
}

const mainGridStyle = {
  display: 'grid',
  gridTemplateColumns: '2fr 1fr',
  gap: 20,
}

const statsColumnStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}
