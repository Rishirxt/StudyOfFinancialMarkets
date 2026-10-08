/**
 * LiveOrderBook — real-time bid/ask depth visualization.
 * Indian Market (NSE) Level-2 Depth aesthetic.
 *
 * Shows asks (red/crimson) and bids (emerald green) as horizontal depth bars.
 * Includes cumulative volume meter, Bid/Ask volume ratio (sentiment gauge),
 * and precise ₹ Indian Rupee pricing.
 */

import { useMemo } from 'react'

export default function LiveOrderBook({ orderBook }) {
  if (!orderBook) {
    return (
      <div style={emptyStyle}>
        <div style={{ fontSize: 28, marginBottom: 6 }}>📑</div>
        <div style={{ fontSize: 13, color: 'var(--dim)', fontWeight: 500 }}>Waiting for NSE order book depth…</div>
      </div>
    )
  }

  const bids = (orderBook.bids || []).slice(0, 8)
  const asks = (orderBook.asks || []).slice(0, 8).reverse() // show asks top-to-bottom, lowest ask at bottom
  
  const totalBidQty = useMemo(() => bids.reduce((acc, b) => acc + b.quantity, 0), [bids])
  const totalAskQty = useMemo(() => asks.reduce((acc, a) => acc + a.quantity, 0), [asks])
  const totalVolume = totalBidQty + totalAskQty
  const bidRatio = totalVolume > 0 ? (totalBidQty / totalVolume) * 100 : 50

  const maxQty = Math.max(
    ...bids.map(b => b.quantity),
    ...asks.map(a => a.quantity),
    1
  )

  return (
    <div style={containerStyle}>
      {/* Sentiment Depth Gauge */}
      <div style={gaugeContainerStyle}>
        <div style={gaugeHeaderStyle}>
          <span style={{ color: 'var(--up)', fontWeight: 600 }}>BUY {bidRatio.toFixed(0)}%</span>
          <span style={{ color: 'var(--dim)', fontSize: 10 }}>TOTAL DEPTH</span>
          <span style={{ color: 'var(--down)', fontWeight: 600 }}>SELL {(100 - bidRatio).toFixed(0)}%</span>
        </div>
        <div style={gaugeBarStyle}>
          <div style={{ width: `${bidRatio}%`, background: 'var(--up)', height: '100%', transition: 'width 0.3s ease' }} />
          <div style={{ width: `${100 - bidRatio}%`, background: 'var(--down)', height: '100%', transition: 'width 0.3s ease' }} />
        </div>
      </div>

      <div style={headerRowStyle}>
        <span style={colHeaderStyle}>Price (₹)</span>
        <span style={colHeaderStyle}>Orders</span>
        <span style={{ ...colHeaderStyle, textAlign: 'right' }}>Volume Depth</span>
      </div>

      {/* ASKS (top, red) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {asks.map((ask, i) => (
          <div key={`ask-${i}`} style={rowStyle}>
            <div style={depthBarStyle(ask.quantity / maxQty, 'var(--down-dim)')} />
            <span style={{ ...priceStyle, color: 'var(--down)' }}>₹{ask.price.toFixed(2)}</span>
            <span style={qtyStyle}>{ask.quantity.toFixed(2)}</span>
            <div style={barContainerStyle}>
              <div style={{
                height: '100%',
                width: `${(ask.quantity / maxQty) * 100}%`,
                background: 'linear-gradient(90deg, rgba(244, 63, 94, 0.2), var(--down))',
                borderRadius: 2,
                transition: 'width 0.25s ease',
              }} />
            </div>
          </div>
        ))}
      </div>

      {/* Spread / Mid-price band */}
      <div style={spreadBandStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={spreadBadgeStyle}>MID</span>
          <span style={midPriceStyle}>
            {orderBook.mid_price ? `₹${orderBook.mid_price.toFixed(2)}` : '—'}
          </span>
        </div>
        <span style={spreadValueStyle}>
          SPREAD: {orderBook.spread ? `₹${orderBook.spread.toFixed(3)}` : '—'}
        </span>
      </div>

      {/* BIDS (bottom, green) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {bids.map((bid, i) => (
          <div key={`bid-${i}`} style={rowStyle}>
            <div style={depthBarStyle(bid.quantity / maxQty, 'var(--up-dim)')} />
            <span style={{ ...priceStyle, color: 'var(--up)' }}>₹{bid.price.toFixed(2)}</span>
            <span style={qtyStyle}>{bid.quantity.toFixed(2)}</span>
            <div style={barContainerStyle}>
              <div style={{
                height: '100%',
                width: `${(bid.quantity / maxQty) * 100}%`,
                background: 'linear-gradient(90deg, rgba(0, 208, 156, 0.2), var(--up))',
                borderRadius: 2,
                transition: 'width 0.25s ease',
              }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const containerStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11.5,
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}

const gaugeContainerStyle = {
  background: 'var(--panel-raised)',
  borderRadius: 6,
  padding: '6px 8px',
  marginBottom: 6,
  border: '1px solid var(--hairline)',
}

const gaugeHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: 10,
  marginBottom: 4,
  fontFamily: 'var(--font-mono)',
}

const gaugeBarStyle = {
  height: 4,
  width: '100%',
  borderRadius: 2,
  overflow: 'hidden',
  display: 'flex',
  background: 'var(--panel-solid)',
}

const headerRowStyle = {
  display: 'grid',
  gridTemplateColumns: '72px 55px 1fr',
  gap: 8,
  marginBottom: 4,
  paddingBottom: 4,
  borderBottom: '1px solid var(--hairline)',
}

const colHeaderStyle = {
  fontSize: 10,
  color: 'var(--dim)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  fontWeight: 600,
}

const rowStyle = {
  display: 'grid',
  gridTemplateColumns: '72px 55px 1fr',
  gap: 8,
  alignItems: 'center',
  padding: '2px 4px',
  position: 'relative',
  borderRadius: 4,
}

const depthBarStyle = (fraction, bg) => ({
  position: 'absolute',
  top: 0,
  left: 0,
  bottom: 0,
  width: `${Math.min(fraction * 100, 100)}%`,
  background: bg,
  opacity: 0.18,
  borderRadius: 3,
  pointerEvents: 'none',
  transition: 'width 0.2s ease',
})

const priceStyle = {
  fontWeight: 600,
  zIndex: 1,
}

const qtyStyle = {
  color: 'var(--ink-dim)',
  zIndex: 1,
}

const barContainerStyle = {
  height: 8,
  borderRadius: 2,
  overflow: 'hidden',
  display: 'flex',
  justifyContent: 'flex-start',
}

const spreadBandStyle = {
  margin: '6px 0',
  padding: '5px 8px',
  background: 'var(--panel-raised)',
  borderRadius: 6,
  border: '1px dashed var(--hairline-bright)',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
}

const spreadBadgeStyle = {
  fontSize: 9,
  fontWeight: 700,
  padding: '2px 5px',
  borderRadius: 3,
  background: 'var(--signal-dim)',
  color: 'var(--signal-bright)',
  letterSpacing: '0.05em',
}

const midPriceStyle = {
  fontWeight: 700,
  color: 'var(--ink-bright)',
  fontSize: 13,
}

const spreadValueStyle = {
  color: 'var(--dim)',
  fontSize: 10,
  letterSpacing: '0.04em',
}

const emptyStyle = {
  height: 220,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--dim)',
  fontFamily: 'var(--font-body)',
  border: '1px dashed var(--hairline)',
  borderRadius: 8,
}
