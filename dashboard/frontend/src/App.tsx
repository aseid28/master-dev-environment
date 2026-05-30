import { useEffect, useState } from 'react'
import { AgentGrid } from './AgentGrid'
import { ApprovalModal } from './ApprovalModal'
import { TerminalPane } from './TerminalPane'
import type { Agent } from './types'

const API = ''  // Vite proxy → backend

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selected, setSelected] = useState<Agent | null>(null)
  const [approving, setApproving] = useState<Agent | null>(null)
  const [error, setError] = useState('')

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API}/agents`)
      if (!res.ok) throw new Error(await res.text())
      setAgents(await res.json())
      setError('')
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => {
    fetchAgents()
    const id = setInterval(fetchAgents, 5000)
    return () => clearInterval(id)
  }, [])

  const handleApprove = async (agent: Agent) => {
    await fetch(`${API}/agents/${agent.session_id}/approve`, { method: 'POST' })
    await fetchAgents()
    setApproving(null)
  }

  const handleReject = async (agent: Agent, feedback: string) => {
    await fetch(`${API}/agents/${agent.session_id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback }),
    })
    await fetchAgents()
    setApproving(null)
  }

  const handleGrantWrite = async (agent: Agent) => {
    await fetch(`${API}/agents/${agent.session_id}/grant-write`, { method: 'POST' })
    await fetchAgents()
  }

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <span style={styles.logo}>⬡ Agent Control</span>
        <span style={styles.count}>{agents.length} sessions</span>
        {error && <span style={styles.error}>{error}</span>}
      </header>

      <main style={{ ...styles.main, gridTemplateColumns: selected ? '380px 1fr' : '1fr' }}>
        <AgentGrid
          agents={agents}
          selected={selected}
          onSelect={setSelected}
          onApprove={setApproving}
          onGrantWrite={handleGrantWrite}
          compact={!!selected}
        />

        {selected && (
          <TerminalPane
            agent={selected}
            onClose={() => setSelected(null)}
          />
        )}
      </main>

      {approving && (
        <ApprovalModal
          agent={approving}
          onApprove={() => handleApprove(approving)}
          onReject={(fb) => handleReject(approving, fb)}
          onClose={() => setApproving(null)}
        />
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    background: '#0f0f0f',
    color: '#e2e8f0',
    fontFamily: 'ui-monospace, "Cascadia Code", monospace',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '12px 24px',
    borderBottom: '1px solid #1e1e1e',
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    background: '#111',
  },
  logo: {
    fontSize: 18,
    fontWeight: 700,
    color: '#7dd3fc',
    letterSpacing: '-0.5px',
  },
  count: {
    fontSize: 12,
    color: '#64748b',
  },
  error: {
    fontSize: 12,
    color: '#f87171',
    marginLeft: 'auto',
  },
  main: {
    flex: 1,
    display: 'grid',
    minHeight: 0,
    overflow: 'hidden',
  },
}
