export interface Agent {
  session_id: string
  project_id: string
  milestone_id: string | null
  status: AgentStatus
  cost_usd: number
  cost_cap_usd: number
  pct_used?: number
  turn_count?: number
  model: string
  last_updated: number
}

export type AgentStatus =
  | 'idle'
  | 'running'
  | 'cleanup'
  | 'awaiting_approval'
  | 'needs_review'
  | 'council_pending'
  | 'complete'
  | 'hard_cap'
  | 'ended'
