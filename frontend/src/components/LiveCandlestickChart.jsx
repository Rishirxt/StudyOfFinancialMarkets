/**
 * LiveCandlestickChart — streaming candlestick chart with live price trace.
 * Institutional NSE Terminal Edition (₹ Currency).
 */

import { useMemo } from 'react'

const WIDTH = 920
const HEIGHT = 370
const VOLUME_HEIGHT = 60
const PADDING = { top: 22, right: 86, bottom: 10, left: 68 }

export default function LiveCandlestickChart({ candles, priceHistory, circuitBreaker, halted }) {
  const { bodies, gridLines, priceLine, yToPixel, yMin, yMax } = useMemo(() => {
    const sourceCandles = candles || []
    const sourcePrices = priceHistory || []
    // Keep the full series in React state, but draw a bounded number of SVG
    // marks. This avoids rebuilding thousands of DOM nodes during long runs.
    const sample = (items, limit) => {
      if (items.length <= limit) return items
      const stride = Math.ceil((items.length - 1) / (limit - 1))
      const sampled = items.filter((_, index) => index % stride === 0)
      if (sampled[sampled.length - 1] !== items[items.length - 1]) sampled.push(items[items.length - 1])
      return sampled
    }
    const allCandles = sample(sourceCandles, 500)
    const allPrices = sample(sourcePrices, 800)

    if (allCandles.length === 0 && allPrices.length === 0) {
      return { bodies: [], gridLines: [], priceLine: [], yToPixel: () => 0, yMin: 90, yMax: 110 }
    }

    let maxPrice = -Infinity
    let minPrice = Infinity
    for (const candle of allCandles) {
      maxPrice = Math.max(maxPrice, candle.high)
      minPrice = Math.min(minPrice, candle.low)
    }
    for (const point of allPrices) {
      maxPrice = Math.max(maxPrice, point.price)
      minPrice = Math.min(minPrice, point.price)
    }
    if (!Number.isFinite(maxPrice)) maxPrice = 110
    if (!Number.isFinite(minPrice)) minPrice = 90
    const pricePad = (maxPrice - minPrice) * 0.1 || 2
    const yMax = maxPrice + pricePad
    const yMin = minPrice - pricePad

    const chartWidth = WIDTH - PADDING.left - PADDING.right
    const chartHeight = HEIGHT - PADDING.top - PADDING.bottom - VOLUME_HEIGHT

    const yToPixel = (price) =>
      PADDING.top + chartHeight * (1 - (price - yMin) / (yMax - yMin))

    const maxVolume = allCandles.reduce((max, candle) => Math.max(max, candle.volume), 1)

    const totalRounds = allPrices.length > 0
      ? allPrices[allPrices.length - 1].round
      : (allCandles.length > 0 ? allCandles[allCandles.length - 1].window_end : 100)

    const roundToX = (round) =>
      PADDING.left + (round / Math.max(totalRounds, 1)) * chartWidth

    const bodies = allCandles.map((c, i) => {
      const xCenter = roundToX((c.window_start + c.window_end) / 2)
      const xWidth = Math.max((c.window_end - c.window_start + 1) / Math.max(totalRounds, 1) * chartWidth * 0.72, 3)
      const isUp = c.close >= c.open
      const bodyTop = yToPixel(Math.max(c.open, c.close))
      const bodyBottom = yToPixel(Math.min(c.open, c.close))
      const volHeight = (c.volume / maxVolume) * (VOLUME_HEIGHT - 8)

      return {
        key: `${c.window_start}-${c.window_end}`,
        x: xCenter,
        wickTop: yToPixel(c.high),
        wickBottom: yToPixel(c.low),
        bodyTop,
        bodyHeight: Math.max(bodyBottom - bodyTop, 1.5),
        isUp,
        candleWidth: xWidth,
        volY: PADDING.top + chartHeight + 10 + (VOLUME_HEIGHT - 8 - volHeight),
        volHeight,
        isLast: i === allCandles.length - 1,
      }
    })

    const priceLine = allPrices.map(p => ({
      x: roundToX(p.round),
      y: yToPixel(p.price),
    }))

    const gridLines = [0, 0.25, 0.5, 0.75, 1.0].map(frac => {
      const price = yMin + (yMax - yMin) * frac
      return { y: yToPixel(price), price }
    })

    return { bodies, gridLines, priceLine, yToPixel, yMin, yMax }
  }, [candles, priceHistory])

  const lastPrice = priceHistory?.length > 0 ? priceHistory[priceHistory.length - 1].price : null
  const lastY = lastPrice !== null ? yToPixel(lastPrice) : null

  if ((!candles || candles.length === 0) && (!priceHistory || priceHistory.length === 0)) {
    return (
      <div style={emptyStyle}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>📊</div>
        <div style={{ fontWeight: 600, color: 'var(--ink)' }}>Live Candlestick Stream Idle</div>
        <div style={{ fontSize: 12, color: 'var(--dim)' }}>Launch the simulation to watch live price action in Indian Rupees (₹).</div>
      </div>
    )
  }

  const pathD = priceLine.length > 1
    ? `M ${priceLine[0].x} ${priceLine[0].y} ` + priceLine.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ')
    : null

  const areaD = pathD && priceLine.length > 1
    ? `${pathD} L ${priceLine[priceLine.length - 1].x} ${HEIGHT - VOLUME_HEIGHT - PADDING.bottom} L ${priceLine[0].x} ${HEIGHT - VOLUME_HEIGHT - PADDING.bottom} Z`
    : null

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width="100%"
      style={{ display: 'block', fontFamily: 'var(--font-mono)', overflow: 'visible' }}
      role="img"
      aria-label="Live candlestick chart of simulated price action in Indian Rupees"
    >
      <defs>
        <style>{`
          @keyframes pulseGlow {
            0%, 100% { opacity: 1; filter: drop-shadow(0 0 3px rgba(0, 208, 156, 0.6)); }
            50% { opacity: 0.5; }
          }
          @keyframes dotPulse {
            0%, 100% { r: 3.5; opacity: 1; }
            50% { r: 6; opacity: 0.5; }
          }
          .candle-live { animation: pulseGlow 1.2s ease-in-out infinite; }
          .live-dot-anim { animation: dotPulse 1.2s ease-in-out infinite; }
        `}</style>
        <linearGradient id="priceAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--signal-bright)" stopOpacity="0.18" />
          <stop offset="100%" stopColor="var(--signal-bright)" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="bullVolGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--up)" stopOpacity="0.6" />
          <stop offset="100%" stopColor="var(--up)" stopOpacity="0.1" />
        </linearGradient>
        <linearGradient id="bearVolGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--down)" stopOpacity="0.6" />
          <stop offset="100%" stopColor="var(--down)" stopOpacity="0.1" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Grid lines & ₹ Price labels */}
      {gridLines.map((g, i) => (
        <g key={i}>
          <line
            x1={PADDING.left} x2={WIDTH - PADDING.right}
            y1={g.y} y2={g.y}
            stroke="var(--hairline)" strokeWidth="1" strokeDasharray="3 5"
          />
          <text x={PADDING.left - 8} y={g.y}
            textAnchor="end" dominantBaseline="middle"
            fontSize="10" fill="var(--dim)" fontWeight="500"
          >
            ₹{g.price.toFixed(2)}
          </text>
        </g>
      ))}

      {/* Circuit Breaker Halt overlay */}
      {halted && (
        <rect
          x={PADDING.left}
          y={PADDING.top}
          width={WIDTH - PADDING.left - PADDING.right}
          height={HEIGHT - PADDING.top - PADDING.bottom}
          fill="rgba(168, 85, 247, 0.08)"
          stroke="var(--circuit)"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          rx="4"
        />
      )}

      {/* Candle bodies and Volume */}
      {bodies.map((b) => (
        <g key={b.key} className={b.isLast ? 'candle-live' : undefined}>
          <line x1={b.x} x2={b.x} y1={b.wickTop} y2={b.wickBottom}
            stroke={b.isUp ? 'var(--up)' : 'var(--down)'} strokeWidth="1.2" />
          <rect
            x={b.x - b.candleWidth / 2} y={b.bodyTop}
            width={b.candleWidth} height={b.bodyHeight}
            fill={b.isUp ? 'var(--up)' : 'var(--down)'}
            rx="1.5"
          />
          {/* Volume bars */}
          <rect
            x={b.x - b.candleWidth / 2}
            y={b.volY}
            width={b.candleWidth} height={b.volHeight}
            fill={b.isUp ? 'url(#bullVolGrad)' : 'url(#bearVolGrad)'}
            rx="1"
          />
        </g>
      ))}

      {/* Price area fill */}
      {areaD && (
        <path d={areaD} fill="url(#priceAreaGrad)" />
      )}

      {/* Live price line */}
      {pathD && (
        <path
          d={pathD}
          fill="none"
          stroke="var(--signal-bright)"
          strokeWidth="1.75"
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity="0.85"
        />
      )}

      {/* Live price badge on right axis */}
      {lastY !== null && lastPrice !== null && (
        <g>
          <line
            x1={PADDING.left} x2={WIDTH - PADDING.right}
            y1={lastY} y2={lastY}
            stroke="var(--signal-bright)" strokeWidth="1"
            strokeDasharray="4 4" opacity="0.6"
          />
          <rect
            x={WIDTH - PADDING.right + 4}
            y={lastY - 12}
            width={78} height={24}
            fill="var(--signal-bright)" rx="5"
            filter="drop-shadow(0 2px 8px rgba(14, 165, 233, 0.4))"
          />
          <text
            x={WIDTH - PADDING.right + 8}
            y={lastY + 1}
            dominantBaseline="middle"
            fontSize="11" fontWeight="700"
            fill="#04060A"
          >
            ₹{lastPrice.toFixed(2)}
          </text>
          <circle cx={WIDTH - PADDING.right} cy={lastY} r="3.5"
            fill="var(--signal-bright)" filter="url(#glow)"
            className="live-dot-anim" />
        </g>
      )}

      {/* Halted banner text */}
      {halted && (
        <g>
          <rect
            x={PADDING.left + (WIDTH - PADDING.left - PADDING.right) / 2 - 160}
            y={PADDING.top + (HEIGHT - PADDING.top - PADDING.bottom - VOLUME_HEIGHT) / 2 - 16}
            width={320} height={32}
            fill="rgba(20, 10, 35, 0.9)"
            stroke="var(--circuit)" strokeWidth="1" rx="6"
          />
          <text
            x={PADDING.left + (WIDTH - PADDING.left - PADDING.right) / 2}
            y={PADDING.top + (HEIGHT - PADDING.top - PADDING.bottom - VOLUME_HEIGHT) / 2 + 1}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="12" fontWeight="700"
            fill="var(--circuit-bright)" letterSpacing="0.08em"
          >
            ⚡ SEBI CIRCUIT FILTER — TRADING HALTED
          </text>
        </g>
      )}
    </svg>
  )
}

const emptyStyle = {
  height: 290,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--dim)',
  fontFamily: 'var(--font-body)',
  fontSize: 14,
  border: '1px dashed var(--hairline-bright)',
  borderRadius: 12,
  gap: 6,
  background: 'var(--panel-raised)',
}
