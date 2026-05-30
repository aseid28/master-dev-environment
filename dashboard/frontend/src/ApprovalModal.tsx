import { useState } from 'react'
import type { Agent } from './types'

interface Props {
  agent: Agent
  onApprove: () => void
  onReject: (feedback: string) => void
  onClose: () => void
}

export function ApprovalModal({ agent, onApprove, onReject, onClose }: Props) {
  const [feedback, setFeedback] = useState('')
  const [mode, setMode] = useState<'review' | 'reject'>('review')

  const handleReject = () => {
    if (!feedback.trim()) return
    onReject(feedback.trim())
  }

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>Milestone Review</div>
            <div style={styles.subtitle}>
              {agent.project_id} · [{agent.milestone_id}]
            </div>
          </div>
          <button style={styles.close} onClick={onClose}>✕</button>
        </div>

        <div style={styles.body}>
          {/* Status summary */}
          <div style={styles.statusBox}>
            <div style={styles.statusRow}>
              <span style={styles.statusLabel}>Status</span>
              <span style={{
                ...styles.statusValue,
                color: agent.status === 'needs_review' ? '#f87171' : '#22c55e',
              }}>
                {agent.status === 'needs_review' ? 'Needs Review' : 'Cleanup Passed ✓'}
              </span>
            </div>
            <div style={styles.statusRow}>
              <span style={styles.statusLabel}>Cost</span>
              <span style={styles.statusValue}>
                ${agent.cost_usd.toFixed(4)} / ${agent.cost_cap_usd.toFixed(2)}
                ({(agent.pct_used ?? 0).toFixed(1)}%)
              </span>
            </div>
            <div style={styles.statusRow}>
              <span style={styles.statusLabel}>Turns</span>
              <span style={styles.statusValue}>{agent.turn_count ?? '—'}</span>
            </div>
          </div>

          {/* Instructions */}
          <div style={styles.instructions}>
            Review the agent's work in the terminal. When ready, approve to advance
            to the next milestone, or reject with specific feedback to resume.
          </div>

          {mode === 'reject' && (
            <div style={styles.feedbackSection}>
              <label style={styles.feedbackLabel}>Feedback for agent</label>
              <textarea
                style={styles.textarea}
                placeholder="Be specific: what needs to change, what was missing, what failed..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                autoFocus
                rows={4}
              />
            </div>
          )}
        </div>

        <div style={styles.footer}>
          {mode === 'review' ? (
            <>
              <button style={btnStyles.reject} onClick={() => setMode('reject')}>
                Reject &amp; Give Feedback
              </button>
              <button style={btnStyles.approve} onClick={onApprove}>
                Approve Milestone ✓
              </button>
            </>
          ) : (
            <>
              <button style={btnStyles.secondary} onClick={() => setMode('review')}>
                ← Back
              </button>
              <button
                style={{ ...btnStyles.reject, opacity: feedback.trim() ? 1 : 0.4 }}
                onClick={handleReject}
                disabled={!feedback.trim()}
              >
                Send Feedback &amp; Resume
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: '#000000cc',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 200,
  },
  modal: {
    width: 520,
    background: '#111',
    border: '1px solid #1e1e1e',
    borderRadius: 10,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '16px 20px',
    borderBottom: '1px solid #1e1e1e',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  title: {
    fontSize: 15,
    fontWeight: 700,
    color: '#f1f5f9',
  },
  subtitle: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
    fontFamily: 'monospace',
  },
  close: {
    background: 'none',
    border: 'none',
    color: '#475569',
    cursor: 'pointer',
    fontSize: 16,
  },
  body: {
    padding: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  statusBox: {
    background: '#0c0c0c',
    border: '1px solid #1e1e1e',
    borderRadius: 6,
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
  },
  statusLabel: {
    color: '#475569',
  },
  statusValue: {
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  instructions: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 1.6,
  },
  feedbackSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  feedbackLabel: {
    fontSize: 11,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  textarea: {
    background: '#0c0c0c',
    border: '1px solid #334155',
    borderRadius: 6,
    color: '#e2e8f0',
    fontFamily: 'ui-monospace, monospace',
    fontSize: 12,
    padding: 10,
    resize: 'vertical',
    outline: 'none',
  },
  footer: {
    padding: '14px 20px',
    borderTop: '1px solid #1e1e1e',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
  },
}

const btnBase: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  padding: '8px 16px',
  borderRadius: 6,
  border: 'none',
  cursor: 'pointer',
  fontFamily: 'inherit',
}

const btnStyles: Record<string, React.CSSProperties> = {
  approve: { ...btnBase, background: '#22c55e', color: '#0c0c0c' },
  reject: { ...btnBase, background: '#f8717122', color: '#f87171', border: '1px solid #f8717144' },
  secondary: { ...btnBase, background: '#1e293b', color: '#94a3b8' },
}
