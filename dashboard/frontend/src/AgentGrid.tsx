import type { Agent, AgentStatus } from './types'

const STATUS_COLOR: Record<AgentStatus, string> = {
  idle: '#475569',
  running: '#22c55e',
  cleanup: '#f59e0b',
  awaiting_approval: '#7dd3fc',
  needs_review: '#f87171',
  council_pending: '#a78bfa',
  complete: '#10b981',
  hard_cap: '#ef4444',
  ended: '#475569',
}

const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: 'Idle',
  running: 'Running',
  cleanup: 'Cleanup',
  awaiting_approval: 'Awaiting Approval',
  needs_review: 'Needs Review',
  council_pending: 'Council Pending',
  complete: 'Complete',
  hard_cap: 'Cap Reached',
  ended: 'Ended',
}

function CostBar({ pct }: { pct: number }) {
  const color = pct >= 100 ? '#ef4444' : pct >= 80 ? '#f59e0b' : '#22c55e'
  return (
    <div style={barStyles.track}>
      <div
        style={{
          ...barStyles.fill,
          width: `${Math.min(pct, 100)}%`,
          background: color,
        }}
      />
      <span style={barStyles.label}>{pct.toFixed(1)}%</span>
    </div>
  )
}

interface Props {
  agents: Agent[]
  selected: Agent | null
  onSelect: (a: Agent) => void
  onApprove: (a: Agent) => void
  onGrantWrite: (a: Agent) => void
  compact?: boolean  // true when terminal pane is open
}

export function AgentGrid({ agents, selected, onSelect, onApprove, onGrantWrite, compact }: Props) {
  if (agents.length === 0) {
    return (
      <div style={gridStyles.empty}>
        No active agent sessions. Launch one with the orchestrator.
      </div>
    )
  }

  return (
    <div style={{ ...gridStyles.grid, gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))' }}>
      {agents.map((agent) => {
        const isSelected = selected?.session_id === agent.session_id
        const pct = agent.pct_used ?? ((agent.cost_usd / agent.cost_cap_usd) * 100)
        const status = agent.status as AgentStatus
        const needsAction = status === 'awaiting_approval' || status === 'needs_review'

        return (
          <div
            key={agent.session_id}
            style={{
              ...cardStyles.card,
              ...(isSelected ? cardStyles.selected : {}),
              ...(needsAction ? cardStyles.needsAction : {}),
            }}
          >
            {/* Header */}
            <div style={cardStyles.header}>
              <span style={cardStyles.projectId}>{agent.project_id}</span>
              <span style={{ ...cardStyles.badge, color: STATUS_COLOR[status] }}>
                ● {STATUS_LABEL[status]}
              </span>
            </div>

            {/* Milestone */}
            <div style={cardStyles.milestone}>
              {agent.milestone_id ? `[${agent.milestone_id}]` : '—'}
            </div>

            {/* Cost bar */}
            <div style={cardStyles.costRow}>
              <span style={cardStyles.costLabel}>
                ${agent.cost_usd.toFixed(4)} / ${agent.cost_cap_usd.toFixed(2)}
              </span>
              <span style={cardStyles.turns}>
                {agent.turn_count != null ? `${agent.turn_count} turns` : ''}
              </span>
            </div>
            <CostBar pct={pct} />

            {/* Session ID */}
            <div style={cardStyles.sessionId}>{agent.session_id}</div>

            {/* Actions */}
            <div style={cardStyles.actions}>
              <button style={btnStyles.secondary} onClick={() => onSelect(agent)}>
                Terminal
              </button>
              {needsAction && (
                <button style={btnStyles.primary} onClick={() => onApprove(agent)}>
                  Review
                </button>
              )}
              {status === 'running' && (
                <button
                  style={btnStyles.warning}
                  onClick={() => onGrantWrite(agent)}
                  title="Grant write permissions for this session"
                >
                  Grant Write
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const gridStyles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid',
    gap: 16,
    padding: 24,
    alignContent: 'start',
    overflowY: 'auto',
  },
  empty: {
    padding: 48,
    textAlign: 'center',
    color: '#475569',
    fontSize: 14,
  },
}

const cardStyles: Record<string, React.CSSProperties> = {
  card: {
    background: '#161616',
    border: '1px solid #1e1e1e',
    borderRadius: 8,
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    cursor: 'default',
    transition: 'border-color 0.15s',
  },
  selected: {
    borderColor: '#7dd3fc',
  },
  needsAction: {
    borderColor: '#7dd3fc',
    boxShadow: '0 0 0 1px #7dd3fc22',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  projectId: {
    fontWeight: 700,
    fontSize: 13,
    color: '#f1f5f9',
  },
  badge: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  milestone: {
    fontSize: 12,
    color: '#94a3b8',
    fontStyle: 'italic',
  },
  costRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 11,
    color: '#64748b',
  },
  costLabel: {},
  turns: {},
  sessionId: {
    fontSize: 10,
    color: '#334155',
    fontFamily: 'monospace',
  },
  actions: {
    display: 'flex',
    gap: 8,
    marginTop: 4,
  },
}

const barStyles: Record<string, React.CSSProperties> = {
  track: {
    height: 4,
    background: '#1e293b',
    borderRadius: 2,
    position: 'relative',
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 2,
    transition: 'width 0.5s ease',
  },
  label: {
    display: 'none',
  },
}

const btnBase: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  padding: '4px 10px',
  borderRadius: 4,
  border: 'none',
  cursor: 'pointer',
  fontFamily: 'inherit',
}

const btnStyles: Record<string, React.CSSProperties> = {
  primary: { ...btnBase, background: '#7dd3fc', color: '#0c0c0c' },
  secondary: { ...btnBase, background: '#1e293b', color: '#94a3b8' },
  warning: { ...btnBase, background: '#f59e0b22', color: '#f59e0b', border: '1px solid #f59e0b44' },
}
