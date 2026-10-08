import { useState } from 'react'

export default function HumanTradingPanel({ enabled, canSubmit, portfolio, results, trades, onSubmit }) {
  const [side, setSide] = useState('buy')
  const [orderType, setOrderType] = useState('market')
  const [quantity, setQuantity] = useState('1')
  const [price, setPrice] = useState('100')
  const [sendMessage, setSendMessage] = useState('')
  const unavailableReason = !enabled
    ? 'Turn on “Human trader order entry” in Regulatory & Risk Controls, then start a new session.'
    : !canSubmit
      ? 'Orders can be submitted while the market session is running.'
      : 'Live order entry is ready.'

  function submit(event) {
    event.preventDefault()
    const sent = onSubmit({
      side,
      order_type: orderType,
      quantity: Number(quantity),
      price: orderType === 'limit' ? Number(price) : null,
    })
    setSendMessage(sent ? 'Order sent; waiting for the next market round.' : 'Order was not sent. Check that the live session is connected and trading is enabled.')
  }

  return (
    <section style={panelStyle} aria-label="Human trading">
      <div style={headerStyle}>
        <div>
          <h3 style={titleStyle}>Manual order entry</h3>
          <p style={subtitleStyle}>{unavailableReason}</p>
        </div>
      </div>

      <div style={portfolioStyle}>
        <Metric label="Cash" value={portfolio ? `₹${portfolio.cash.toFixed(2)}` : '—'} />
        <Metric label="Holdings" value={portfolio ? portfolio.holdings.toFixed(4) : '—'} />
        <Metric label="Portfolio" value={portfolio ? `₹${portfolio.portfolio_value.toFixed(2)}` : '—'} />
        <Metric label="P&L" value={portfolio ? `₹${portfolio.pnl.toFixed(2)}` : '—'} />
      </div>

      <form onSubmit={submit} style={formStyle}>
        <label style={fieldStyle}>Side
          <select value={side} onChange={event => setSide(event.target.value)} style={inputStyle}>
            <option value="buy">BUY</option><option value="sell">SELL</option>
          </select>
        </label>
        <label style={fieldStyle}>Type
          <select value={orderType} onChange={event => setOrderType(event.target.value)} style={inputStyle}>
            <option value="market">MARKET</option><option value="limit">LIMIT</option>
          </select>
        </label>
        <label style={fieldStyle}>Quantity
          <input type="number" min="0.01" step="0.01" value={quantity} onChange={event => setQuantity(event.target.value)} style={inputStyle} required />
        </label>
        {orderType === 'limit' && <label style={fieldStyle}>Limit price
          <input type="number" min="0.01" step="0.01" value={price} onChange={event => setPrice(event.target.value)} style={inputStyle} required />
        </label>}
        <button style={{ ...submitStyle, ...(!enabled || !canSubmit ? disabledSubmitStyle : {}) }} disabled={!enabled || !canSubmit}>Submit order</button>
      </form>
      {sendMessage && <div role="status" style={{ ...mutedStyle, marginTop: -10, marginBottom: 14 }}>{sendMessage}</div>}

      <div style={columnsStyle}>
        <div>
          <h4 style={sectionTitle}>Order results</h4>
          {results.length ? results.slice(0, 5).map((result, index) => (
            <div key={`${result.order_id ?? 'rejected'}-${index}`} style={rowStyle}>
              <span>{result.status}{result.order_id ? ` · #${result.order_id}` : ''}</span>
              {result.error && <span style={{ color: 'var(--down)' }}>{result.error}</span>}
              {result.fills?.length > 0 && <span>{result.fills.length} fill(s)</span>}
            </div>
          )) : <div style={mutedStyle}>No orders submitted this session.</div>}
        </div>
        <div>
          <h4 style={sectionTitle}>Human trade history</h4>
          {trades.length ? trades.slice(0, 5).map(trade => (
            <div key={trade.trade_id} style={rowStyle}>
              <span>Round {trade.round} · {trade.side.toUpperCase()} {trade.quantity.toFixed(2)}</span>
              <span>₹{trade.price.toFixed(2)}</span>
            </div>
          )) : <div style={mutedStyle}>Fills from your orders appear here.</div>}
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value }) {
  return <div><div style={metricValue}>{value}</div><div style={metricLabel}>{label}</div></div>
}

const panelStyle = { background: 'var(--panel)', border: '1px solid var(--hairline)', borderRadius: 12, padding: 18, marginBottom: 16 }
const headerStyle = { marginBottom: 14 }
const titleStyle = { margin: 0, fontSize: 15, color: 'var(--ink-bright)' }
const subtitleStyle = { margin: '3px 0 0', color: 'var(--dim)', fontSize: 12 }
const portfolioStyle = { display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10, marginBottom: 14 }
const metricValue = { color: 'var(--ink-bright)', fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700 }
const metricLabel = { color: 'var(--dim)', fontSize: 10, textTransform: 'uppercase' }
const formStyle = { display: 'flex', alignItems: 'end', gap: 10, flexWrap: 'wrap', marginBottom: 18 }
const fieldStyle = { display: 'grid', gap: 4, color: 'var(--ink-dim)', fontSize: 11 }
const inputStyle = { minWidth: 100, padding: '8px 10px', border: '1px solid var(--hairline-bright)', borderRadius: 6, color: 'var(--ink)', background: 'var(--panel-solid)' }
const submitStyle = { padding: '9px 16px', borderRadius: 7, background: 'var(--signal)', color: '#fff', fontWeight: 700 }
const disabledSubmitStyle = { background: 'var(--panel-solid)', color: 'var(--dim)', cursor: 'not-allowed', opacity: 0.7 }
const columnsStyle = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }
const sectionTitle = { margin: '0 0 8px', color: 'var(--ink-dim)', fontSize: 11, textTransform: 'uppercase' }
const rowStyle = { display: 'flex', justifyContent: 'space-between', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--hairline)', color: 'var(--ink)', fontSize: 11 }
const mutedStyle = { color: 'var(--dim)', fontSize: 11 }
