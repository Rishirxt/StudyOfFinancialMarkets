import { lazy, Suspense, useState, useEffect } from 'react'
import { useMarketStream } from './hooks/useMarketStream.js'
import { runSimulation, runPhaseDiagram, runHysteresis } from './api.js'
const LiveCandlestickChart = lazy(() => import('./components/LiveCandlestickChart.jsx'))
const LiveOrderBook = lazy(() => import('./components/LiveOrderBook.jsx'))
const AgentWealthPanel = lazy(() => import('./components/AgentWealthPanel.jsx'))
const MarketEventLog = lazy(() => import('./components/MarketEventLog.jsx'))
const CandlestickChart = lazy(() => import('./components/CandlestickChart.jsx'))
const PhaseDiagramHeatmap = lazy(() => import('./components/PhaseDiagramHeatmap.jsx'))
const HysteresisChart = lazy(() => import('./components/HysteresisChart.jsx'))
const LeverageExperimentPanel = lazy(() => import('./components/LeverageExperimentPanel.jsx'))
const CircuitBreakerPanel = lazy(() => import('./components/CircuitBreakerPanel.jsx'))

// ── Navigation Tabs ──────────────────────────────────────────────────────────
const TABS = [
  { id: 'live', label: 'Live Market (NSE)', icon: '📡' },
  { id: 'leverage', label: 'F&O Leverage Cascades', icon: '⚡' },
  { id: 'circuit', label: 'SEBI Circuit Breakers', icon: '🛡️' },
  { id: 'phase', label: 'Phase Transitions', icon: '🗺️' },
  { id: 'hysteresis', label: 'Market Hysteresis', icon: '🔁' },
  { id: 'static', label: 'Batch Experiments', icon: '📊' },
]

// Speed presets (ms delay between rounds)
const SPEED_PRESETS = [
  { label: '🐢 0.25x', ms: 500, desc: 'Ultra Slow / Deep Inspection' },
  { label: '▶ 0.5x', ms: 350, desc: 'Realistic Pace' },
  { label: '⚡ 1.0x', ms: 220, desc: 'Standard Simulation' },
  { label: '⏩ 2.0x', ms: 100, desc: 'Fast Analysis' },
  { label: '🚀 5.0x', ms: 30, desc: 'Max Velocity' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('live')
  const [istTime, setIstTime] = useState('')

  // IST Clock updater
  useEffect(() => {
    function updateClock() {
      const now = new Date()
      // Format as IST time (UTC+5:30)
      const options = {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }
      setIstTime(new Intl.DateTimeFormat('en-IN', options).format(now) + ' IST')
    }
    updateClock()
    const timer = setInterval(updateClock, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div style={appStyle}>
      {/* ── TOP LIVE TICKER TAPE (INDIAN MARKET INDICES) ────────────────── */}
      <div className="ticker-tape-container">
        <div className="ticker-tape-track">
          <div className="ticker-item">
            <span style={{ color: 'var(--saffron)', fontWeight: 700 }}>🇮🇳 NSE/BSE SIMULATED MARKET</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>NIFTY 50:</span>
            <span style={{ color: 'var(--up)', fontWeight: 600 }}>₹22,468.50 (+0.42%) ▲</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>SENSEX:</span>
            <span style={{ color: 'var(--up)', fontWeight: 600 }}>₹74,192.10 (+0.38%) ▲</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>BANK NIFTY:</span>
            <span style={{ color: 'var(--down)', fontWeight: 600 }}>₹48,150.80 (-0.15%) ▼</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>ACTIVE ASSET (BHARAT-100):</span>
            <span style={{ color: 'var(--signal-bright)', fontWeight: 600 }}>LIVE ORDER BOOK</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--circuit-bright)' }}>SEBI SURVEILLANCE:</span>
            <span style={{ color: 'var(--ink-dim)' }}>DYNAMIC CIRCUIT LIMITS ON</span>
          </div>
          {/* Duplicate for seamless marquee effect */}
          <div className="ticker-item">
            <span style={{ color: 'var(--saffron)', fontWeight: 700 }}>🇮🇳 NSE/BSE SIMULATED MARKET</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>NIFTY 50:</span>
            <span style={{ color: 'var(--up)', fontWeight: 600 }}>₹22,468.50 (+0.42%) ▲</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>SENSEX:</span>
            <span style={{ color: 'var(--up)', fontWeight: 600 }}>₹74,192.10 (+0.38%) ▲</span>
          </div>
          <div className="ticker-item">
            <span style={{ color: 'var(--ink-dim)' }}>BANK NIFTY:</span>
            <span style={{ color: 'var(--down)', fontWeight: 600 }}>₹48,150.80 (-0.15%) ▼</span>
          </div>
        </div>
      </div>

      {/* ── HEADER NAVIGATION BAR ─────────────────────────────────────── */}
      <header style={headerStyle}>
        <div style={headerLeftStyle}>
          <div style={logoWrapperStyle}>
            <div style={logoBadgeStyle}>BHARAT</div>
            <div style={logoStyle}>
              EXCHANGE <span style={{ color: 'var(--signal-bright)' }}>SIM</span>
            </div>
          </div>
          <div style={headerBadgeStyle}>
            <span style={headerDotStyle} />
            <span>NSE/BSE AGENT-BASED LOB</span>
          </div>
        </div>

        <nav style={tabBarStyle}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              style={tabStyle(activeTab === tab.id)}
              onClick={() => setActiveTab(tab.id)}
              id={`tab-${tab.id}`}
            >
              <span style={{ fontSize: 14 }}>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>

        <div style={headerRightStyle}>
          <div style={clockBadgeStyle}>
            <span style={{ color: 'var(--saffron)' }}>🕒</span>
            <span>{istTime || '15:30:00 IST'}</span>
          </div>
        </div>
      </header>

      {/* ── MAIN TAB CONTENT ─────────────────────────────────────────── */}
      <main style={mainStyle}>
        <Suspense fallback={<div style={descStyle}>Loading experiment…</div>}>
          {activeTab === 'live' && <LiveMarketTab />}
          {activeTab === 'leverage' && <LeverageExperimentPanel />}
          {activeTab === 'circuit' && <CircuitBreakerPanel />}
          {activeTab === 'phase' && <PhaseDiagramTab />}
          {activeTab === 'hysteresis' && <HysteresisTab />}
          {activeTab === 'static' && <StaticSimTab />}
        </Suspense>
      </main>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// LIVE MARKET TAB (INDIAN RUPEE + SPEED CONTROLS)
// ═══════════════════════════════════════════════════════════════════════════════

function LiveMarketTab() {
  const stream = useMarketStream()

  const [config, setConfig] = useState({
    fundamentalist_count: 8,
    trend_follower_count: 6,
    noise_count: 8,
    leveraged_count: 0,
    reaction_sensitivity: 1.2,
    num_rounds: 200,
    candle_window: 5,
    seed: 42,
    round_delay_ms: 250, // Default to a smooth, observable pace (250ms)
    circuit_breaker_enabled: false,
    circuit_breaker_threshold_pct: 5.0,
    circuit_breaker_halt_duration: 3,
    leverage_ratio: 3.0,
    margin_call_threshold: 0.3,
  })

  function updateConfig(key, val) {
    setConfig(c => ({ ...c, [key]: val }))
  }

  const isRunning = stream.status === 'running' || stream.status === 'halted'
  const isDone = stream.status === 'done'
  const isConnecting = stream.status === 'connecting'
  const isError = stream.status === 'error'

  const priceChg = stream.priceHistory.length >= 2
    ? stream.latestPrice - stream.priceHistory[0].price
    : 0
  const priceChgPct = stream.priceHistory.length >= 2
    ? (priceChg / stream.priceHistory[0].price) * 100
    : 0
  const progressPct = stream.totalRounds > 0
    ? (stream.currentRound / stream.totalRounds) * 100
    : 0

  return (
    <div>
      {/* ── CONTROL PANEL ─────────────────────────────────────────── */}
      <div style={controlPanelStyle}>
        <div style={controlPanelTopStyle}>
          <div>
            <h2 style={panelTitleStyle}>🇮🇳 Market Configuration & Engine Controls</h2>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--dim)' }}>
              Configure trading participant population, execution tick speed, and SEBI regulatory circuit filters.
            </p>
          </div>

          <div style={controlButtonsStyle}>
            {isRunning || isConnecting ? (
              <div style={{ display: 'flex', gap: 8 }}>
                {/* Pause / Resume Button */}
                {stream.isPaused ? (
                  <button style={resumeBtnStyle} onClick={stream.resume} id="btn-resume-sim">
                    <span>▶</span> Resume Inspection
                  </button>
                ) : (
                  <button style={pauseBtnStyle} onClick={stream.pause} id="btn-pause-sim">
                    <span>⏸</span> Pause Market
                  </button>
                )}
                {/* Stop Button */}
                <button style={stopBtnStyle} onClick={stream.stop} id="btn-stop-sim">
                  <span>⏹</span> Abort Session
                </button>
              </div>
            ) : (
              <button
                style={launchBtnStyle}
                onClick={() => stream.start(config)}
                id="btn-launch-sim"
                disabled={isConnecting}
              >
                <span style={liveDotInlineStyle} className="live-dot" />
                {isConnecting ? 'Connecting to Order Book…' : 'Launch Live Market (₹)'}
              </button>
            )}
          </div>
        </div>

        {/* ── SPEED PRESET SELECTOR BAR ───────────────────────────── */}
        <div style={speedBannerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 14 }}>⏱️</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
              Market Movement Speed:
            </span>
            <span style={{ fontSize: 11, color: 'var(--signal-bright)', fontFamily: 'var(--font-mono)' }}>
              {config.round_delay_ms} ms / round
            </span>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {SPEED_PRESETS.map((preset) => (
              <button
                key={preset.ms}
                onClick={() => updateConfig('round_delay_ms', preset.ms)}
                style={speedPresetBtnStyle(config.round_delay_ms === preset.ms)}
                title={preset.desc}
              >
                {preset.label} ({preset.ms}ms)
              </button>
            ))}
          </div>
        </div>

        <div style={controlGridStyle}>
          {/* Population */}
          <ControlSection title="👥 Market Participant Ledger">
            <SliderRow label="Value Fundamentalists" value={config.fundamentalist_count}
              min={0} max={20} onChange={v => updateConfig('fundamentalist_count', v)}
              color="var(--fundamentalist)" id="slider-fundamentalists" />
            <SliderRow label="Momentum Chartist Traders" value={config.trend_follower_count}
              min={0} max={20} onChange={v => updateConfig('trend_follower_count', v)}
              color="var(--trend-follower)" id="slider-trend-followers" />
            <SliderRow label="Retail Noise Liquidity" value={config.noise_count}
              min={0} max={20} onChange={v => updateConfig('noise_count', v)}
              color="var(--noise-trader)" id="slider-noise-traders" />
            <SliderRow label="High-Leverage F&O Speculators" value={config.leveraged_count}
              min={0} max={10} onChange={v => updateConfig('leveraged_count', v)}
              color="var(--leveraged)" id="slider-leveraged" />
          </ControlSection>

          {/* Execution Params */}
          <ControlSection title="⚙️ Execution & Pacing">
            <SliderRow label="Chartist Sensitivity" value={config.reaction_sensitivity}
              min={0.1} max={4} step={0.1} onChange={v => updateConfig('reaction_sensitivity', v)}
              id="slider-sensitivity" />
            <SliderRow label="Total Rounds" value={config.num_rounds}
              min={50} max={500} step={25} onChange={v => updateConfig('num_rounds', v)}
              id="slider-rounds" />
            <SliderRow label="Candle Aggregation Window" value={config.candle_window}
              min={3} max={20} onChange={v => updateConfig('candle_window', v)}
              id="slider-candle-window" />
            <SliderRow label="Custom Delay (ms/round)" value={config.round_delay_ms}
              min={20} max={800} step={20} onChange={v => updateConfig('round_delay_ms', v)}
              id="slider-speed" />
          </ControlSection>

          {/* Experiments & SEBI Circuit Breakers */}
          <ControlSection title="🛡️ Regulatory & Risk Controls">
            <div style={toggleRowStyle}>
              <label style={toggleLabelStyle} htmlFor="toggle-circuit-breaker">
                <span style={{ color: 'var(--circuit-bright)' }}>⚡</span> SEBI Circuit Breaker
              </label>
              <ToggleSwitch
                id="toggle-circuit-breaker"
                checked={config.circuit_breaker_enabled}
                onChange={v => updateConfig('circuit_breaker_enabled', v)}
                color="var(--circuit-bright)"
              />
            </div>
            {config.circuit_breaker_enabled && (
              <div style={subControlsStyle}>
                <SliderRow label="Cool-off Trigger (%)" value={config.circuit_breaker_threshold_pct}
                  min={1} max={20} step={0.5}
                  onChange={v => updateConfig('circuit_breaker_threshold_pct', v)}
                  color="var(--circuit-bright)" id="slider-cb-threshold" />
                <SliderRow label="Halt Window (rounds)" value={config.circuit_breaker_halt_duration}
                  min={1} max={10}
                  onChange={v => updateConfig('circuit_breaker_halt_duration', v)}
                  color="var(--circuit-bright)" id="slider-cb-duration" />
              </div>
            )}

            {config.leveraged_count > 0 && (
              <div style={subControlsStyle}>
                <div style={subTitleStyle}>⚡ F&O Leverage Constraints</div>
                <SliderRow label="Leverage Multiplier" value={config.leverage_ratio}
                  min={1} max={10} step={0.5}
                  onChange={v => updateConfig('leverage_ratio', v)}
                  color="var(--leverage)" id="slider-leverage-ratio" />
                <SliderRow label="Margin Call Threshold" value={config.margin_call_threshold}
                  min={0.05} max={0.5} step={0.05}
                  onChange={v => updateConfig('margin_call_threshold', v)}
                  color="var(--leverage)" id="slider-margin-threshold" />
              </div>
            )}
          </ControlSection>
        </div>
      </div>

      {/* ── LIVE MARKET STATUS BAR (INR ₹ TICKER) ────────────────────── */}
      {(isRunning || isDone || isError || isConnecting) && (
        <div style={statusBarStyle(stream.status)}>
          <div style={statusLeftStyle}>
            {stream.isPaused ? (
              <span className="paused-dot" />
            ) : isRunning ? (
              <span className={stream.status === 'halted' ? 'halted-dot' : 'live-dot'} />
            ) : null}
            {isDone && <span style={{ color: 'var(--up)' }}>✓</span>}
            {isError && <span style={{ color: 'var(--down)' }}>✗</span>}
            <span style={statusTextStyle}>
              {stream.isPaused ? '⏸ SESSION PAUSED — INSPECTION MODE' :
               stream.status === 'halted' ? '⚡ SEBI CIRCUIT FILTER — TRADING SUSPENDED' :
               stream.status === 'running' ? `LIVE BHARAT-100 — Round ${stream.currentRound} / ${stream.totalRounds}` :
               stream.status === 'done' ? `MARKET CLOSE — ${stream.totalRounds} rounds completed` :
               stream.status === 'error' ? 'DISCONNECTED FROM EXCHANGE ENGINE' :
               'OPENING CO-LOCATION FEED…'}
            </span>
          </div>

          <div style={statusRightStyle}>
            {/* Big Rupee Price Ticker */}
            <span style={priceTickerStyle(stream.priceDirection)}>
              ₹{stream.latestPrice.toFixed(2)}
            </span>
            <span style={priceChangeStyle(priceChg >= 0)}>
              {priceChg >= 0 ? '+' : ''}₹{priceChg.toFixed(2)} ({priceChgPct >= 0 ? '+' : ''}{priceChgPct.toFixed(2)}%)
            </span>
            {stream.marginCallCount > 0 && (
              <span style={marginCallCountStyle}>
                ⚠️ {stream.marginCallCount} Margin Calls
              </span>
            )}
            {stream.circuitBreaker && stream.circuitBreaker.halt_count > 0 && (
              <span style={cbCountStyle}>
                ⚡ {stream.circuitBreaker.halt_count} Circuit Halt{stream.circuitBreaker.halt_count > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Progress bar */}
          <div style={progressBarTrackStyle}>
            <div style={progressBarFillStyle(progressPct, stream.status, stream.isPaused)} />
          </div>
        </div>
      )}

      {/* ── MAIN CHART + SIDE PANELS ────────────────────────────────── */}
      <div style={marketGridStyle}>
        {/* Center: Live Candlestick & Price Chart */}
        <div style={chartPanelStyle}>
          <PanelHeader
            title="📈 BHARAT-100 Real-Time Candlestick Price Action"
            subtitle={
              stream.candles.length > 0
                ? `${stream.candles.length} candles · ${stream.priceHistory.length} trade points · All quotes in INR (₹)`
                : 'Awaiting round stream initiation…'
            }
          />
          <LiveCandlestickChart
            candles={stream.candles}
            priceHistory={stream.priceHistory}
            circuitBreaker={stream.circuitBreaker}
            halted={stream.status === 'halted'}
          />
        </div>

        {/* Right column: Order Book + Agent Wealth */}
        <div style={sidePanelColumnStyle}>
          <div style={panelStyle}>
            <PanelHeader title="📋 Level-2 Order Depth (NSE)" subtitle="Live resting limit orders (₹)" />
            <LiveOrderBook orderBook={stream.orderBook} />
          </div>
          <div style={panelStyle}>
            <PanelHeader title="👥 Participant Capital" subtitle="Real-time capital balance (₹)" />
            <AgentWealthPanel agentWealth={stream.agentWealth} latestPrice={stream.latestPrice} />
          </div>
        </div>
      </div>

      {/* ── BOTTOM ROW: Surveillance Event Log + Round Stats ─────────── */}
      <div style={bottomRowStyle}>
        <div style={{ ...panelStyle, flex: 1.6 }}>
          <PanelHeader title="📡 Surveillance Trade Tape & Logs" subtitle="Chronological market orders, fills, and regulatory events" />
          <MarketEventLog events={stream.eventLog} />
        </div>
        <div style={{ ...panelStyle, flex: 1 }}>
          <PanelHeader title="📊 Round Metrics" subtitle="Active equilibrium parameters" />
          <LiveStatsPanel stream={stream} priceChg={priceChg} priceChgPct={priceChgPct} />
        </div>
      </div>
    </div>
  )
}

function LiveStatsPanel({ stream, priceChg, priceChgPct }) {
  return (
    <div style={statsGridStyle}>
      <StatCell
        label="Last Traded Price"
        value={`₹${stream.latestPrice.toFixed(2)}`}
        color={stream.priceDirection === 'up' ? 'var(--up)' : stream.priceDirection === 'down' ? 'var(--down)' : 'var(--ink)'}
      />
      <StatCell
        label="Session Return"
        value={`${priceChg >= 0 ? '+' : ''}${priceChgPct.toFixed(2)}%`}
        color={priceChg >= 0 ? 'var(--up)' : 'var(--down)'}
      />
      <StatCell label="Current Round" value={`${stream.currentRound} / ${stream.totalRounds || '—'}`} />
      <StatCell label="Active Agents" value={stream.agentWealth.length} />
      <StatCell
        label="Force Liquidations"
        value={stream.marginCallCount}
        color={stream.marginCallCount > 0 ? 'var(--down)' : 'var(--ink)'}
      />
      <StatCell
        label="Circuit Halts"
        value={stream.circuitBreaker?.halt_count ?? 0}
        color={stream.circuitBreaker?.halt_count > 0 ? 'var(--circuit-bright)' : 'var(--ink)'}
      />
      <StatCell
        label="LOB Spread"
        value={stream.orderBook?.spread ? `₹${stream.orderBook.spread.toFixed(3)}` : '—'}
      />
      <StatCell
        label="Mid-Market Price"
        value={stream.orderBook?.mid_price ? `₹${stream.orderBook.mid_price.toFixed(2)}` : '—'}
      />
    </div>
  )
}

function StatCell({ label, value, color }) {
  return (
    <div style={statCellStyle}>
      <div style={{ ...statValueStyle2, color: color || 'var(--ink)' }}>{value}</div>
      <div style={statLabelStyle2}>{label}</div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE DIAGRAM TAB
// ═══════════════════════════════════════════════════════════════════════════════

function PhaseDiagramTab() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const r = await runPhaseDiagram({})
      setResult(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={panelStyle}>
        <PanelHeader
          title="🗺️ Phase Transition Diagram (Stability Frontier)"
          subtitle="Sweeps trend-follower population density × reaction sensitivity to detect regime shifts."
        />
        <p style={descStyle}>
          Each cell in the heatmap computes the return volatility in the Indian market order book for a given
          combination of momentum traders and feedback aggressiveness. High volatility indicates endogenous market collapse.
        </p>
        <button style={primaryBtnStyle} onClick={run} disabled={loading} id="btn-phase-sweep">
          {loading ? <><SpinnerDot /> Simulating Parameter Grid…</> : '🗺️ Execute Phase Transition Sweep'}
        </button>
        {error && <div style={errorStyle}>{error}</div>}
        <div style={{ marginTop: 20 }}>
          <PhaseDiagramHeatmap data={result} />
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// HYSTERESIS TAB
// ═══════════════════════════════════════════════════════════════════════════════

function HysteresisTab() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const r = await runHysteresis({})
      setResult(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={panelStyle}>
        <PanelHeader
          title="🔁 Market Hysteresis & Equilibrium Scarring"
          subtitle="Ramps momentum sensitivity past the crash threshold, then completely reverses it to test memory."
        />
        <p style={descStyle}>
          Investigates whether a crashed Indian stock market returns symmetrically to its original baseline price,
          or whether the crash leaves a permanent hysteresis scar due to order book liquidity depletion.
        </p>
        {result && (
          <div style={hysteresisSummaryStyle}>
            <SummaryCard label="Pre-Shock Price" value={`₹${result.pre_mean_price?.toFixed(2)}`} />
            <SummaryCard label="Post-Recovery Price" value={`₹${result.post_mean_price?.toFixed(2)}`} />
            <SummaryCard label="Permanent Shift"
              value={`${result.price_shift_pct?.toFixed(2)}%`}
              color={Math.abs(result.price_shift_pct) > 1 ? 'var(--leverage)' : 'var(--up)'} />
            <SummaryCard label="Volatility Scar Ratio"
              value={result.volatility_ratio?.toFixed(3)}
              color={result.volatility_ratio > 1.1 ? 'var(--down)' : 'var(--up)'} />
          </div>
        )}
        <button style={primaryBtnStyle} onClick={run} disabled={loading} id="btn-hysteresis">
          {loading ? <><SpinnerDot /> Running Hysteresis Experiment…</> : '🔁 Run Hysteresis Ramp Experiment'}
        </button>
        {error && <div style={errorStyle}>{error}</div>}
        <div style={{ marginTop: 20 }}>
          <HysteresisChart data={result} />
        </div>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, color }) {
  return (
    <div style={summaryCardStyle}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: color || 'var(--ink)' }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 3 }}>{label}</div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// BATCH RUN TAB
// ═══════════════════════════════════════════════════════════════════════════════

function StaticSimTab() {
  const [params, setParams] = useState({
    fundamentalist_count: 8,
    trend_follower_count: 6,
    noise_count: 8,
    reaction_sensitivity: 1.2,
    num_rounds: 300,
    seed: 42,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const r = await runSimulation(params)
      setResult(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={panelStyle}>
        <PanelHeader title="📊 High-Volume Batch Experiment" subtitle="Runs a full simulation synchronously and computes stylized market facts." />
        <div style={controlGridStyle}>
          <ControlSection title="👥 Agent Roster">
            <SliderRow label="Fundamentalists" value={params.fundamentalist_count}
              min={0} max={20} onChange={v => setParams(p => ({ ...p, fundamentalist_count: v }))}
              color="var(--fundamentalist)" id="static-slider-fund" />
            <SliderRow label="Trend-followers" value={params.trend_follower_count}
              min={0} max={20} onChange={v => setParams(p => ({ ...p, trend_follower_count: v }))}
              color="var(--trend-follower)" id="static-slider-tf" />
            <SliderRow label="Noise Traders" value={params.noise_count}
              min={0} max={20} onChange={v => setParams(p => ({ ...p, noise_count: v }))}
              color="var(--noise-trader)" id="static-slider-noise" />
          </ControlSection>
          <ControlSection title="⚙️ Experiment Parameters">
            <SliderRow label="Reaction Sensitivity" value={params.reaction_sensitivity}
              min={0.1} max={4} step={0.1}
              onChange={v => setParams(p => ({ ...p, reaction_sensitivity: v }))}
              id="static-slider-sens" />
            <SliderRow label="Total Rounds" value={params.num_rounds}
              min={50} max={1000} step={50}
              onChange={v => setParams(p => ({ ...p, num_rounds: v }))}
              id="static-slider-rounds" />
          </ControlSection>
        </div>
        <button style={primaryBtnStyle} onClick={run} disabled={loading} id="btn-batch-run">
          {loading ? <><SpinnerDot /> Processing Batch…</> : '📊 Run Batch Simulation'}
        </button>
        {error && <div style={errorStyle}>{error}. Is the backend running?</div>}
        {result && (
          <div style={{ marginTop: 22 }}>
            <div style={hysteresisSummaryStyle}>
              <SummaryCard label="Final Settlement Price" value={`₹${result.final_price.toFixed(2)}`} />
              <SummaryCard label="Total Executed Fills" value={result.total_trades} />
              <SummaryCard label="Candlesticks Aggregated" value={result.candles?.length} />
              <SummaryCard label="Settlement Spread"
                value={result.order_book_snapshot?.spread ? `₹${result.order_book_snapshot.spread.toFixed(3)}` : '—'} />
            </div>
            <CandlestickChart candles={result.candles} />
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SHARED UI CONTROLS
// ═══════════════════════════════════════════════════════════════════════════════

function PanelHeader({ title, subtitle }) {
  return (
    <div style={panelHeaderStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {subtitle && <p style={panelSubtitleStyle}>{subtitle}</p>}
    </div>
  )
}

function ControlSection({ title, children }) {
  return (
    <div style={controlSectionStyle}>
      <div style={controlSectionTitleStyle}>{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {children}
      </div>
    </div>
  )
}

function SliderRow({ label, value, min, max, step = 1, onChange, color, id }) {
  return (
    <label style={sliderRowStyle} htmlFor={id}>
      <div style={sliderLabelRowStyle}>
        <span style={{ color: color || 'var(--ink-dim)', fontWeight: 500 }}>{label}</span>
        <span style={sliderValueStyle}>{value}</span>
      </div>
      <input
        id={id}
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={sliderInputStyle(color)}
      />
    </label>
  )
}

function ToggleSwitch({ id, checked, onChange, color }) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={toggleStyle(checked, color)}
    >
      <div style={toggleThumbStyle(checked)} />
    </button>
  )
}

function SpinnerDot() {
  return (
    <span style={{ display: 'inline-block', marginRight: 6, animation: 'pulse-dot 0.8s infinite' }}>
      ⏳
    </span>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// STYLES & LAYOUT OBJECTS
// ═══════════════════════════════════════════════════════════════════════════════

const appStyle = {
  minHeight: '100vh',
  background: 'var(--void)',
}

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 24px',
  height: 64,
  background: 'var(--panel)',
  borderBottom: '1px solid var(--hairline)',
  position: 'sticky',
  top: 0,
  zIndex: 100,
  backdropFilter: 'var(--glass-blur)',
}

const headerLeftStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 14,
}

const logoWrapperStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
}

const logoBadgeStyle = {
  background: 'linear-gradient(135deg, var(--saffron) 0%, #EA580C 100%)',
  color: '#FFFFFF',
  fontFamily: 'var(--font-display)',
  fontSize: 10,
  fontWeight: 800,
  letterSpacing: '0.1em',
  padding: '3px 7px',
  borderRadius: 4,
}

const logoStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: 18,
  fontWeight: 800,
  letterSpacing: '0.04em',
  color: 'var(--ink-bright)',
}

const headerBadgeStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '4px 10px',
  borderRadius: 20,
  background: 'rgba(255, 255, 255, 0.04)',
  border: '1px solid var(--hairline)',
  fontSize: 10.5,
  fontFamily: 'var(--font-mono)',
  color: 'var(--dim)',
  letterSpacing: '0.05em',
}

const headerDotStyle = {
  width: 6,
  height: 6,
  borderRadius: '50%',
  background: 'var(--up)',
  boxShadow: '0 0 6px var(--up)',
}

const tabBarStyle = {
  display: 'flex',
  gap: 4,
  background: 'rgba(5, 8, 14, 0.6)',
  padding: '4px',
  borderRadius: 10,
  border: '1px solid var(--hairline)',
}

const tabStyle = (active) => ({
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '7px 14px',
  borderRadius: 8,
  border: 'none',
  background: active ? 'rgba(14, 165, 233, 0.18)' : 'transparent',
  color: active ? 'var(--signal-bright)' : 'var(--dim)',
  fontFamily: 'var(--font-body)',
  fontSize: 12.5,
  fontWeight: active ? 600 : 500,
  cursor: 'pointer',
  transition: 'all 0.18s ease',
  boxShadow: active ? '0 0 12px rgba(14, 165, 233, 0.15), inset 0 0 0 1px rgba(14, 165, 233, 0.3)' : 'none',
})

const headerRightStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
}

const clockBadgeStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  fontFamily: 'var(--font-mono)',
  fontSize: 11.5,
  color: 'var(--ink)',
  background: 'var(--panel-raised)',
  padding: '5px 10px',
  borderRadius: 6,
  border: '1px solid var(--hairline)',
}

const mainStyle = {
  maxWidth: 1440,
  margin: '0 auto',
  padding: '20px 24px 60px',
}

const panelStyle = {
  background: 'var(--panel)',
  border: '1px solid var(--hairline)',
  borderRadius: 'var(--radius-lg)',
  padding: '20px',
  marginBottom: 16,
  backdropFilter: 'var(--glass-blur)',
  boxShadow: 'var(--card-shadow)',
}

const panelHeaderStyle = {
  marginBottom: 16,
}

const panelTitleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: 15.5,
  fontWeight: 700,
  margin: '0 0 4px',
  color: 'var(--ink-bright)',
}

const panelSubtitleStyle = {
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  color: 'var(--dim)',
  margin: 0,
  lineHeight: 1.5,
}

const controlPanelStyle = {
  background: 'var(--panel)',
  border: '1px solid var(--hairline)',
  borderRadius: 'var(--radius-lg)',
  padding: '20px',
  marginBottom: 16,
  backdropFilter: 'var(--glass-blur)',
  boxShadow: 'var(--card-shadow)',
}

const controlPanelTopStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  marginBottom: 16,
  gap: 16,
  flexWrap: 'wrap',
}

const controlButtonsStyle = {
  display: 'flex',
  gap: 10,
  alignItems: 'center',
}

const speedBannerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  background: 'rgba(14, 165, 233, 0.06)',
  border: '1px solid rgba(14, 165, 233, 0.16)',
  borderRadius: 8,
  padding: '8px 12px',
  marginBottom: 16,
  flexWrap: 'wrap',
  gap: 10,
}

const speedPresetBtnStyle = (active) => ({
  background: active ? 'var(--signal-bright)' : 'var(--panel-raised)',
  color: active ? '#04060A' : 'var(--ink)',
  border: `1px solid ${active ? 'var(--signal-bright)' : 'var(--hairline)'}`,
  borderRadius: 6,
  padding: '4px 10px',
  fontSize: 11,
  fontWeight: active ? 700 : 500,
  fontFamily: 'var(--font-mono)',
  cursor: 'pointer',
  transition: 'all 0.15s ease',
  boxShadow: active ? '0 0 10px var(--signal-glow)' : 'none',
})

const launchBtnStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  background: 'linear-gradient(135deg, var(--up) 0%, #059669 100%)',
  color: '#04060A',
  border: 'none',
  borderRadius: 8,
  padding: '10px 22px',
  fontSize: 13.5,
  fontWeight: 700,
  fontFamily: 'var(--font-body)',
  cursor: 'pointer',
  letterSpacing: '0.02em',
  boxShadow: '0 0 24px rgba(0, 208, 156, 0.35)',
}

const pauseBtnStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  background: 'rgba(255, 153, 51, 0.14)',
  color: 'var(--saffron)',
  border: '1px solid var(--saffron)',
  borderRadius: 8,
  padding: '10px 16px',
  fontSize: 13,
  fontWeight: 600,
  fontFamily: 'var(--font-body)',
  cursor: 'pointer',
}

const resumeBtnStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  background: 'rgba(0, 208, 156, 0.16)',
  color: 'var(--up)',
  border: '1px solid var(--up)',
  borderRadius: 8,
  padding: '10px 16px',
  fontSize: 13,
  fontWeight: 600,
  fontFamily: 'var(--font-body)',
  cursor: 'pointer',
}

const stopBtnStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  background: 'var(--down-dim)',
  color: 'var(--down)',
  border: '1px solid var(--down)',
  borderRadius: 8,
  padding: '10px 16px',
  fontSize: 13,
  fontWeight: 600,
  fontFamily: 'var(--font-body)',
  cursor: 'pointer',
}

const liveDotInlineStyle = {
  display: 'inline-block',
}

const controlGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: 16,
}

const controlSectionStyle = {
  background: 'var(--panel-raised)',
  border: '1px solid var(--hairline)',
  borderRadius: 10,
  padding: '14px 16px',
}

const controlSectionTitleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: 11.5,
  fontWeight: 700,
  color: 'var(--ink)',
  marginBottom: 12,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
}

const sliderRowStyle = {
  display: 'block',
  cursor: 'pointer',
}

const sliderLabelRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  color: 'var(--dim)',
  marginBottom: 5,
}

const sliderValueStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  color: 'var(--signal-bright)',
  fontWeight: 600,
}

const sliderInputStyle = (color) => ({
  width: '100%',
  accentColor: color || 'var(--signal-bright)',
  cursor: 'pointer',
})

const toggleRowStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: 8,
}

const toggleLabelStyle = {
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  color: 'var(--ink-dim)',
  fontWeight: 500,
  display: 'flex',
  alignItems: 'center',
  gap: 6,
}

const toggleStyle = (checked, color) => ({
  width: 38,
  height: 20,
  borderRadius: 10,
  border: 'none',
  background: checked ? (color || 'var(--signal-bright)') : 'var(--hairline-bright)',
  cursor: 'pointer',
  padding: 2,
  display: 'flex',
  alignItems: 'center',
  transition: 'background 0.2s',
  justifyContent: checked ? 'flex-end' : 'flex-start',
})

const toggleThumbStyle = (checked) => ({
  width: 16,
  height: 16,
  borderRadius: '50%',
  background: '#FFFFFF',
  boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
  transition: 'all 0.2s',
})

const subControlsStyle = {
  marginTop: 10,
  paddingTop: 10,
  borderTop: '1px solid var(--hairline)',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const subTitleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: 11,
  color: 'var(--leverage)',
  fontWeight: 700,
  marginBottom: 4,
  letterSpacing: '0.04em',
}

const statusBarStyle = (status) => ({
  background: status === 'halted' ? 'rgba(168, 85, 247, 0.12)' :
              status === 'done' ? 'rgba(0, 208, 156, 0.08)' :
              status === 'error' ? 'var(--down-dim)' :
              'rgba(14, 165, 233, 0.08)',
  border: `1px solid ${
    status === 'halted' ? 'var(--circuit-bright)' :
    status === 'done' ? 'var(--up)' :
    status === 'error' ? 'var(--down)' :
    'var(--hairline-bright)'
  }`,
  borderRadius: 12,
  padding: '12px 18px 8px',
  marginBottom: 16,
  position: 'relative',
  overflow: 'hidden',
  backdropFilter: 'var(--glass-blur)',
  boxShadow: '0 8px 24px -4px rgba(0,0,0,0.4)',
})

const statusLeftStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  marginBottom: 6,
}

const statusTextStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: '0.06em',
  color: 'var(--ink-dim)',
}

const statusRightStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 14,
  marginBottom: 8,
  flexWrap: 'wrap',
}

const priceTickerStyle = (direction) => ({
  fontFamily: 'var(--font-mono)',
  fontSize: 32,
  fontWeight: 800,
  color: direction === 'up' ? 'var(--up)' : direction === 'down' ? 'var(--down)' : 'var(--ink-bright)',
  letterSpacing: '-0.02em',
  transition: 'color 0.25s',
})

const priceChangeStyle = (isUp) => ({
  fontFamily: 'var(--font-mono)',
  fontSize: 15,
  color: isUp ? 'var(--up)' : 'var(--down)',
  fontWeight: 600,
})

const marginCallCountStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--down)',
  background: 'var(--down-dim)',
  border: '1px solid var(--down)',
  padding: '3px 8px',
  borderRadius: 4,
  fontWeight: 700,
}

const cbCountStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--circuit-bright)',
  background: 'var(--circuit-dim)',
  border: '1px solid var(--circuit-bright)',
  padding: '3px 8px',
  borderRadius: 4,
  fontWeight: 700,
}

const progressBarTrackStyle = {
  height: 4,
  background: 'var(--hairline-bright)',
  borderRadius: 2,
  overflow: 'hidden',
  marginTop: 4,
}

const progressBarFillStyle = (pct, status, isPaused) => ({
  height: '100%',
  width: `${pct}%`,
  background: isPaused ? 'var(--saffron)' :
              status === 'halted' ? 'var(--circuit-bright)' :
              status === 'done' ? 'var(--up)' :
              'var(--signal-bright)',
  borderRadius: 2,
  transition: 'width 0.3s ease',
})

const marketGridStyle = {
  display: 'grid',
  gridTemplateColumns: '1fr 340px',
  gap: 16,
  marginBottom: 16,
}

const chartPanelStyle = {
  background: 'var(--panel)',
  border: '1px solid var(--hairline)',
  borderRadius: 'var(--radius-lg)',
  padding: '20px',
  backdropFilter: 'var(--glass-blur)',
  boxShadow: 'var(--card-shadow)',
}

const sidePanelColumnStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}

const bottomRowStyle = {
  display: 'flex',
  gap: 16,
  flexWrap: 'wrap',
}

const statsGridStyle = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: 10,
}

const statCellStyle = {
  padding: '10px 12px',
  background: 'var(--panel-raised)',
  borderRadius: 8,
  border: '1px solid var(--hairline)',
}

const statValueStyle2 = {
  fontFamily: 'var(--font-mono)',
  fontSize: 16,
  fontWeight: 700,
  marginBottom: 2,
}

const statLabelStyle2 = {
  fontFamily: 'var(--font-body)',
  fontSize: 9.5,
  color: 'var(--dim)',
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  fontWeight: 600,
}

const primaryBtnStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  background: 'linear-gradient(135deg, var(--signal) 0%, #0EA5E9 100%)',
  color: '#FFFFFF',
  border: 'none',
  borderRadius: 8,
  padding: '11px 24px',
  fontSize: 13.5,
  fontWeight: 700,
  fontFamily: 'var(--font-body)',
  cursor: 'pointer',
  boxShadow: '0 0 20px rgba(14,165,233,0.3)',
}

const descStyle = {
  fontFamily: 'var(--font-body)',
  fontSize: 13,
  color: 'var(--ink-dim)',
  lineHeight: 1.7,
  marginBottom: 16,
  maxWidth: 720,
}

const errorStyle = {
  marginTop: 12,
  color: 'var(--down)',
  fontSize: 12,
  fontFamily: 'var(--font-body)',
  background: 'var(--down-dim)',
  padding: '8px 12px',
  borderRadius: 6,
  border: '1px solid var(--down)',
}

const hysteresisSummaryStyle = {
  display: 'flex',
  gap: 12,
  marginBottom: 16,
  flexWrap: 'wrap',
}

const summaryCardStyle = {
  background: 'var(--panel-raised)',
  border: '1px solid var(--hairline)',
  borderRadius: 10,
  padding: '14px 18px',
  minWidth: 140,
}
