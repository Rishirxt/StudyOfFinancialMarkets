/**
 * MarketEventLog — scrolling live feed of market events.
 * Indian Market Surveillance & Trade Tape.
 */

const EVENT_STYLES = {
  init: { color: 'var(--signal-bright)', icon: '🇮🇳' },
  round: { color: 'var(--ink-dim)', icon: '•' },
  high_volume: { color: 'var(--ink-bright)', icon: '📊' },
  circuit_breaker: { color: 'var(--circuit-bright)', icon: '⚡' },
  margin_call: { color: 'var(--down)', icon: '🔴' },
  done: { color: 'var(--up)', icon: '✅' },
  summary: { color: 'var(--saffron)', icon: '📋' },
  error: { color: 'var(--down)', icon: '❌' },
}

export default function MarketEventLog({ events }) {
  if (!events || events.length === 0) {
    return (
      <div style={emptyStyle}>
        <div style={{ fontSize: 22, marginBottom: 4 }}>📡</div>
        <div style={{ fontSize: 12, color: 'var(--dim)', fontWeight: 500 }}>
          Surveillance trade tape awaiting round activity…
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {events.map((event) => {
        const style = EVENT_STYLES[event.type] || EVENT_STYLES.round
        return (
          <div key={event.id} style={entryStyle(style.color)} className="event-entry">
            <span style={roundStyle}>R{event.round.toString().padStart(3, '0')}</span>
            <span style={{ marginRight: 4 }}>{style.icon}</span>
            <span style={{ ...messageStyle, color: style.color }}>{event.message}</span>
          </div>
        )
      })}
    </div>
  )
}

const containerStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 3,
  maxHeight: 250,
  overflowY: 'auto',
  fontFamily: 'var(--font-mono)',
  paddingRight: 4,
}

const entryStyle = (color) => ({
  display: 'flex',
  gap: 6,
  padding: '4px 6px',
  borderBottom: '1px solid var(--hairline)',
  alignItems: 'center',
  borderRadius: 4,
  background: 'rgba(255, 255, 255, 0.015)',
  transition: 'background 0.15s ease',
})

const roundStyle = {
  fontSize: 10,
  color: 'var(--dim)',
  minWidth: 36,
  letterSpacing: '0.04em',
  fontWeight: 600,
}

const messageStyle = {
  fontSize: 11.5,
  flex: 1,
  wordBreak: 'break-word',
}

const emptyStyle = {
  height: 140,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--dim)',
  fontFamily: 'var(--font-body)',
  border: '1px dashed var(--hairline)',
  borderRadius: 8,
}
