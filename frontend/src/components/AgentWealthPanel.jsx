/**
 * AgentWealthPanel — shows distribution of agent portfolio values in real-time.
 * Indian Market (NSE) participant wealth breakdown in ₹ (INR).
 */

import { useMemo } from 'react'

const TYPE_CONFIG = {
  fundamentalist: { label: 'Value / Institutional', color: 'var(--fundamentalist)', emoji: '🏛️' },
  trend_follower: { label: 'Momentum / Chartist', color: 'var(--trend-follower)', emoji: '📈' },
  noise_trader: { label: 'Retail / Liquidity', color: 'var(--noise-trader)', emoji: '🎲' },
  leveraged_trader: { label: 'Margin / F&O Trader', color: 'var(--leveraged)', emoji: '⚡' },
}

function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 0,
  }).format(val)
}

export default function AgentWealthPanel({ agentWealth, humanPortfolio }) {
  const groups = useMemo(() => {
    const participants = [...(agentWealth || [])]
    if (humanPortfolio) {
      const humanRow = {
        id: 'human',
        type: 'human',
        cash: humanPortfolio.cash,
        holdings: humanPortfolio.holdings,
        portfolio_value: humanPortfolio.portfolio_value,
      }
      const existingHuman = participants.findIndex(agent => agent.id === 'human' || agent.type === 'human')
      if (existingHuman >= 0) participants[existingHuman] = humanRow
      else participants.push(humanRow)
    }
    if (participants.length === 0) return []

    const byType = {}
    for (const agent of participants) {
      if (!byType[agent.type]) byType[agent.type] = []
      byType[agent.type].push(agent)
    }

    return Object.entries(byType).map(([type, agents]) => {
      const values = agents.map(a => a.portfolio_value)
      const avg = values.reduce((s, v) => s + v, 0) / values.length
      const min = Math.min(...values)
      const max = Math.max(...values)
      const marginCalls = agents.filter(a => a.in_margin_call).length
      const cfg = TYPE_CONFIG[type] || { label: type, color: 'var(--dim)', emoji: '🤖' }
      return { type, agents, avg, min, max, marginCalls, ...cfg }
    })
  }, [agentWealth, humanPortfolio])

  const maxAvg = useMemo(() => Math.max(...groups.map(g => g.avg), 10_000), [groups])

  if (groups.length === 0) {
    return (
      <div style={emptyStyle}>
        <div style={{ fontSize: 26, marginBottom: 6 }}>👥</div>
        <div style={{ fontSize: 12, color: 'var(--dim)', fontWeight: 500 }}>
          Agent ledger updates dynamically per round…
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {groups.map(group => (
        <div key={group.type} style={groupStyle(group.marginCalls > 0)}>
          <div style={groupHeaderStyle}>
            <span style={{ fontSize: 16 }}>{group.emoji}</span>
            <span style={{ ...groupLabelStyle, color: group.color }}>{group.label}</span>
            <span style={countStyle}>{group.agents.length} traders</span>
            {group.marginCalls > 0 && (
              <span style={marginCallBadgeStyle}>
                ⚠️ {group.marginCalls} MARGIN LIQUIDATION
              </span>
            )}
          </div>

          {/* Relative Wealth bar */}
          <div style={barTrackStyle}>
            <div style={{
              height: '100%',
              width: `${Math.min((group.avg / maxAvg) * 100, 100)}%`,
              background: group.marginCalls > 0 
                ? 'var(--down)' 
                : `linear-gradient(90deg, ${group.color}88, ${group.color})`,
              borderRadius: 3,
              transition: 'width 0.35s ease',
            }} />
          </div>

          <div style={statsRowStyle}>
            <div style={statBoxStyle}>
              <div style={statValueStyle}>₹{formatINR(group.avg)}</div>
              <div style={statLabelStyle}>Avg Capital</div>
            </div>
            <div style={statBoxStyle}>
              <div style={{ ...statValueStyle, color: 'var(--down)' }}>₹{formatINR(group.min)}</div>
              <div style={statLabelStyle}>Lowest</div>
            </div>
            <div style={statBoxStyle}>
              <div style={{ ...statValueStyle, color: 'var(--up)' }}>₹{formatINR(group.max)}</div>
              <div style={statLabelStyle}>Highest</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

const containerStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const groupStyle = (isMarginCalled) => ({
  background: isMarginCalled ? 'var(--down-dim)' : 'var(--panel-raised)',
  border: `1px solid ${isMarginCalled ? 'var(--down)' : 'var(--hairline)'}`,
  borderRadius: 8,
  padding: '8px 10px',
  transition: 'all 0.25s ease',
  boxShadow: isMarginCalled ? '0 0 12px var(--down-dim)' : 'none',
})

const groupHeaderStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  marginBottom: 6,
}

const groupLabelStyle = {
  fontWeight: 600,
  fontSize: 12,
  fontFamily: 'var(--font-display)',
}

const countStyle = {
  fontSize: 10.5,
  color: 'var(--dim)',
  marginLeft: 'auto',
  fontFamily: 'var(--font-mono)',
}

const marginCallBadgeStyle = {
  background: 'var(--down)',
  color: '#FFFFFF',
  fontSize: 9,
  fontWeight: 700,
  padding: '2px 6px',
  borderRadius: 4,
  letterSpacing: '0.04em',
}

const barTrackStyle = {
  height: 4,
  background: 'var(--panel-solid)',
  borderRadius: 2,
  overflow: 'hidden',
  marginBottom: 8,
}

const statsRowStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: 6,
}

const statBoxStyle = {
  background: 'rgba(0, 0, 0, 0.25)',
  padding: '4px 6px',
  borderRadius: 4,
  border: '1px solid var(--hairline)',
}

const statValueStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  fontWeight: 600,
  color: 'var(--ink-bright)',
}

const statLabelStyle = {
  fontSize: 9,
  color: 'var(--dim)',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  marginTop: 1,
}

const emptyStyle = {
  height: 180,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--dim)',
  fontFamily: 'var(--font-body)',
  border: '1px dashed var(--hairline)',
  borderRadius: 8,
}
