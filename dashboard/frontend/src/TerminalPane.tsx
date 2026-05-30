import { useEffect, useRef, useCallback } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import type { Agent } from './types'

interface Props {
  agent: Agent
  onClose: () => void
}

// session_id format is run_id; project_id is separate on the agent object
function terminalWsUrl(agent: Agent): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  // Backend runs on port 8080 in prod; Vite proxies /agents in dev but not WS, so use direct
  const port = import.meta.env.DEV ? '8080' : window.location.port
  return `${proto}//${host}:${port}/agents/${agent.project_id}/${agent.session_id}/terminal`
}

export function TerminalPane({ agent, onClose }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    if (!containerRef.current) return

    // Init xterm
    const term = new Terminal({
      theme: {
        background: '#0c0c0c',
        foreground: '#e2e8f0',
        cursor: '#7dd3fc',
        selectionBackground: '#7dd3fc33',
        black: '#0c0c0c',
        brightBlack: '#334155',
        blue: '#7dd3fc',
        brightBlue: '#38bdf8',
        green: '#22c55e',
        brightGreen: '#4ade80',
        red: '#f87171',
        brightRed: '#ef4444',
        yellow: '#fbbf24',
        brightYellow: '#f59e0b',
        magenta: '#a78bfa',
        brightMagenta: '#8b5cf6',
        cyan: '#34d399',
        brightCyan: '#10b981',
        white: '#e2e8f0',
        brightWhite: '#f8fafc',
      },
      fontFamily: '"Cascadia Code", "JetBrains Mono", "Fira Code", ui-monospace, monospace',
      fontSize: 13,
      lineHeight: 1.3,
      cursorBlink: true,
      scrollback: 5000,
      convertEol: true,
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.loadAddon(new WebLinksAddon())
    term.open(containerRef.current)
    fit.fit()

    termRef.current = term
    fitRef.current = fit

    // WebSocket connection
    const ws = new WebSocket(terminalWsUrl(agent))
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onopen = () => {
      // Send initial size
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    }

    ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(e.data))
      } else {
        term.write(e.data)
      }
    }

    ws.onclose = () => {
      term.write('\r\n\x1b[90m[connection closed]\x1b[0m\r\n')
    }

    ws.onerror = () => {
      term.write('\r\n\x1b[31m[connection error — is the backend running?]\x1b[0m\r\n')
    }

    // Terminal input → WebSocket (read-only: suppress input)
    // Comment out the line below to allow interactive input
    // term.onData((data) => ws.readyState === WebSocket.OPEN && ws.send(data))

    return () => {
      ws.close()
      term.dispose()
    }
  }, [agent])

  // Handle window resize
  useEffect(() => {
    const onResize = () => {
      fitRef.current?.fit()
      const term = termRef.current
      const ws = wsRef.current
      if (term && ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const cleanup = connect()
    return cleanup
  }, [connect])

  const pct = agent.pct_used ?? ((agent.cost_usd / agent.cost_cap_usd) * 100)
  const barColor = pct >= 100 ? '#ef4444' : pct >= 80 ? '#f59e0b' : '#22c55e'

  return (
    <div style={styles.panel}>
      {/* Header with status overlay */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.projectId}>{agent.project_id}</span>
          <span style={styles.slash}>/</span>
          <span style={styles.runId}>{agent.session_id}</span>
          {agent.milestone_id && (
            <span style={styles.milestone}>[{agent.milestone_id}]</span>
          )}
        </div>
        <div style={styles.headerRight}>
          {/* Inline cost bar */}
          <div style={styles.costWrap}>
            <span style={styles.costText}>
              ${agent.cost_usd.toFixed(3)} / ${agent.cost_cap_usd.toFixed(2)}
            </span>
            <div style={styles.barTrack}>
              <div style={{ ...styles.barFill, width: `${Math.min(pct, 100)}%`, background: barColor }} />
            </div>
            <span style={{ ...styles.pct, color: barColor }}>{pct.toFixed(0)}%</span>
          </div>
          <button style={styles.close} onClick={onClose}>✕</button>
        </div>
      </div>

      {/* xterm.js mount point */}
      <div ref={containerRef} style={styles.terminal} />

      <div style={styles.footer}>
        Read-only view &nbsp;·&nbsp;
        <code style={styles.code}>
          tmux attach-session -t agent-{agent.project_id}-{agent.session_id}
        </code>
        &nbsp;to interact
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    background: '#0c0c0c',
    borderLeft: '1px solid #1e1e1e',
    height: '100%',
    minHeight: 0,
  },
  header: {
    padding: '8px 14px',
    borderBottom: '1px solid #1e1e1e',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    fontFamily: 'monospace',
    overflow: 'hidden',
  },
  projectId: { color: '#7dd3fc', fontWeight: 700 },
  slash: { color: '#334155' },
  runId: { color: '#64748b' },
  milestone: {
    background: '#1e293b',
    color: '#94a3b8',
    padding: '1px 6px',
    borderRadius: 3,
    fontSize: 11,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flexShrink: 0,
  },
  costWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    color: '#64748b',
  },
  costText: { whiteSpace: 'nowrap' },
  barTrack: {
    width: 60,
    height: 3,
    background: '#1e293b',
    borderRadius: 2,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 2,
    transition: 'width 0.5s ease',
  },
  pct: { fontSize: 10, fontWeight: 600, minWidth: 28 },
  close: {
    background: 'none',
    border: 'none',
    color: '#475569',
    cursor: 'pointer',
    fontSize: 15,
    padding: '2px 4px',
    lineHeight: 1,
  },
  terminal: {
    flex: 1,
    minHeight: 0,
    padding: '4px 0',
    // xterm.js injects its own DOM here
  },
  footer: {
    padding: '6px 14px',
    borderTop: '1px solid #1e1e1e',
    fontSize: 11,
    color: '#334155',
    flexShrink: 0,
  },
  code: {
    color: '#475569',
    fontFamily: 'monospace',
  },
}
