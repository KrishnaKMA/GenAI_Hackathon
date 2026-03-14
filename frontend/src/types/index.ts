// ─────────────────────────────────────────────────────────
// TypeScript types — mirrors backend models/schemas.py
// DO NOT rename fields — they must match the API response exactly.
// ─────────────────────────────────────────────────────────

export type NodeType = 'CLAIMANT' | 'PROVIDER' | 'REPAIR_SHOP' | 'ADJUSTER'
export type EdgeType = 'repaired_by' | 'treated_by' | 'referred_to' | 'shared_incident' | 'filed_by'
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type ClaimStatus = 'pending' | 'analyzed' | 'flagged' | 'approved' | 'rejected'
export type UserRole = 'adjuster' | 'investigator' | 'admin'
export type Decision = 'FLAGGED' | 'APPROVED'

export interface GraphNode {
  id: string
  type: NodeType
  fraud_score: number
  claim_count: number
  is_flagged: boolean
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
  edge_type: EdgeType
  timestamp: string
}

export interface GNNEvidence {
  source_token: string
  target_token: string
  edge_type: string
  importance_score: number
  human_label: string
}

export interface SHAPFeature {
  feature_name: string
  value: number
  contribution: number
  direction: 'increases_risk' | 'decreases_risk'
}

export interface FraudAnalysisResult {
  gnn_score: number
  isolation_score: number
  combined_score: number
  risk_level: RiskLevel
  graph_nodes: GraphNode[]
  graph_edges: GraphEdge[]
  gnn_evidence: GNNEvidence[]
  shap_features: SHAPFeature[]
}

export interface InvestigatorReport {
  claim_token: string
  analysis: FraudAnalysisResult
  narrative: string
  factsheet_id: string
  generated_at: string
}

export interface ClaimRecord {
  claim_token: string
  claim_amount: number
  claim_type: string
  incident_date: string
  filing_date: string
  prior_claim_count: number
  days_since_last_claim: number | null
  claimant_token: string
  provider_token: string
  repair_shop_token: string | null
  adjuster_id: string
  status: ClaimStatus
  created_at: string
  combined_score: number | null
  risk_level: RiskLevel | null
}

export interface ClaimInput {
  claimant_name: string
  provider_name: string
  repair_shop_name?: string
  claim_amount: number
  claim_type: 'auto_repair' | 'medical' | 'property' | 'liability'
  incident_date: string
  filing_date: string
  prior_claim_count: number
  days_since_last_claim?: number
  adjuster_id: string
}

export interface AgentStepUpdate {
  step_id: number
  name: string
  status: 'pending' | 'running' | 'complete' | 'error'
  result?: string
  is_warning?: boolean
  siu_letter?: string
}

export interface FactsheetEntry {
  factsheet_id: string
  claim_token: string
  timestamp: string
  model_version: string
  combined_score: number
  risk_level: RiskLevel
  adjuster_id: string
  decision: Decision
}

export interface User {
  username: string
  role: UserRole
}

export interface LoginResponse {
  access_token: string
  token_type: string
  role: UserRole
  username: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
}
