import { useMemo } from 'react'

const WIDTH = 900
const HEIGHT = 380
const VOLUME_HEIGHT = 70
const PADDING = { top: 16, right: 16, bottom: 8, left: 56 }

export default function CandlestickChart({ candles }) {
  const { bodies, priceScale, volumeScale, gridLines } = useMemo(() => {
    if (!candles || candles.length === 0) {
      return { bodies: [], priceScale: null, volumeScale: null, gridLines: [] }
    }

    const highs = candles.map((c) => c.high)
    const lows = candles.map((c) => c.low)
    const maxPrice = Math.max(...highs)
    const minPrice = Math.min(...lows)
    const pricePad = (maxPrice - minPrice) * 0.08 || 1
    const yMax = maxPrice + pricePad
    const yMin = minPrice - pricePad

    const maxVolume = Math.max(...candles.map((c) => c.volume), 1)

    const chartWidth = WIDTH - PADDING.left - PADDING.right
    const chartHeight = HEIGHT - PADDING.top - PADDING.bottom - VOLUME_HEIGHT
    const slotWidth = chartWidth / candles.length
    const candleWidth = Math.max(slotWidth * 0.55, 2)

    const yToPixel = (price) =>
      PADDING.top + chartHeight * (1 - (price - yMin) / (yMax - yMin))

    const bodies = candles.map((c, i) => {
      const x = PADDING.left + i * slotWidth + slotWidth / 2
      const isUp = c.close >= c.open
      const bodyTop = yToPixel(Math.max(c.open, c.close))
      const bodyBottom = yToPixel(Math.min(c.open, c.close))
      const volHeight = (c.volume / maxVolume) * (VOLUME_HEIGHT - 8)

      return {
        x,
        wickTop: yToPixel(c.high),
        wickBottom: yToPixel(c.low),
        bodyTop,
        bodyHeight: Math.max(bodyBottom - bodyTop, 1),
        isUp,
        candleWidth,
        volY: PADDING.top + chartHeight + 8 + (VOLUME_HEIGHT - 8 - volHeight),
        volHeight,
        isLast: i === candles.length - 1,
        key: `${c.window_start}-${c.window_end}`,
      }
    })

    const gridLines = [0, 0.25, 0.5, 0.75, 1].map((frac) => {
      const price = yMin + (yMax - yMin) * frac
      return { y: yToPixel(price), price }
    })

    return { bodies, priceScale: { yMin, yMax }, volumeScale: { maxVolume }, gridLines }
  }, [candles])

  if (!candles || candles.length === 0) {
    return (
      <div style={emptyStateStyle}>
        Run a simulation to see the candlestick chart.
      </div>
    )
  }

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width="100%"
      style={{ display: 'block', fontFamily: 'var(--font-mono)' }}
      role="img"
      aria-label="Candlestick chart of simulated price action"
    >
      <style>{`
        @keyframes pulseGlow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.55; }
        }
        .candle-live { animation: pulseGlow 1.6s ease-in-out infinite; }
      `}</style>

      {gridLines.map((g, i) => (
        <g key={i}>
          <line
            x1={PADDING.left} x2={WIDTH - PADDING.right}
            y1={g.y} y2={g.y}
            stroke="var(--hairline)" strokeWidth="1"
          />
          <text
            x={PADDING.left - 8} y={g.y}
            textAnchor="end" dominantBaseline="middle"
            fontSize="11" fill="var(--dim)"
          >
            {g.price.toFixed(2)}
          </text>
        </g>
      ))}

      {bodies.map((b) => (
        <g key={b.key} className={b.isLast ? 'candle-live' : undefined}>
          <line
            x1={b.x} x2={b.x}
            y1={b.wickTop} y2={b.wickBottom}
            stroke={b.isUp ? 'var(--up)' : 'var(--down)'}
            strokeWidth="1"
          />
          <rect
            x={b.x - b.candleWidth / 2}
            y={b.bodyTop}
            width={b.candleWidth}
            height={b.bodyHeight}
            fill={b.isUp ? 'var(--up)' : 'var(--down)'}
          />
          <rect
            x={b.x - b.candleWidth / 2}
            y={b.volY}
            width={b.candleWidth}
            height={b.volHeight}
            fill={b.isUp ? 'var(--up)' : 'var(--down)'}
            opacity="0.35"
          />
        </g>
      ))}
    </svg>
  )
}

const emptyStateStyle = {
  height: 300,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--dim)',
  fontFamily: 'var(--font-body)',
  fontSize: 14,
  border: '1px dashed var(--hairline)',
  borderRadius: 8,
}
