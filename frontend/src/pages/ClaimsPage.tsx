import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ClaimRecord, RiskLevel, ClaimStatus } from '../types'
import { claimsApi, analysisApi, cacheReport } from '../lib/api'
import { MOCK_CLAIMS } from '../lib/mockData'
import { ClaimsTable } from '../components/ClaimsTable'

const RISK_FILTERS: (RiskLevel | 'ALL')[] = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const STATUS_FILTERS: (ClaimStatus | 'ALL')[] = ['ALL', 'pending', 'flagged', 'approved', 'analyzed']

export function ClaimsPage() {
  const navigate = useNavigate()
  const [claims, setClaims]       = useState<ClaimRecord[]>([])
  const [loading, setLoading]     = useState(true)
  const [riskFilter, setRisk]     = useState<RiskLevel | 'ALL'>('ALL')
  const [statusFilter, setStatus] = useState<ClaimStatus | 'ALL'>('ALL')
  const [offset, setOffset]       = useState(0)
  const LIMIT = 20

  useEffect(() => {
    let cancelled = false

    const fetchClaims = async () => {
      setLoading(prev => prev && claims.length === 0)
      try {
        const data = await claimsApi.list({
          limit:      LIMIT,
          offset,
          risk_level: riskFilter === 'ALL' ? undefined : riskFilter,
          status:     statusFilter === 'ALL' ? undefined : statusFilter,
        })
        if (!cancelled) {
          setClaims(data)
        }
      } catch {
        if (!cancelled && claims.length === 0) {
          setClaims(MOCK_CLAIMS)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchClaims()
    return () => { cancelled = true }
  }, [riskFilter, statusFilter, offset])

  const handleAnalyze = async (token: string) => {
    try {
      const report = await analysisApi.analyze(token)
      cacheReport(report)
      navigate(`/report/${token}`)
    } catch {
      navigate(`/report/${token}`)
    }
  }

  const pillStyle = (active: boolean): React.CSSProperties => ({
    background:   active ? 'linear-gradient(135deg, #57B7F8, #4B7CF4)' : 'var(--panel-soft)',
    color:        active ? '#08111f' : 'var(--muted)',
    border:       active ? 'none' : '1px solid var(--border)',
    borderRadius: '9999px',
    padding:      '4px 12px',
    fontSize:     '0.75rem',
    fontWeight:   active ? 600 : 500,
    cursor:       'pointer',
    fontFamily:   'Inter, sans-serif',
    transition:   'all 0.12s ease',
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>All Claims</h1>
        <button onClick={() => navigate('/claims/new')} className="btn-primary">+ Submit Claim</button>
      </div>

      {/* Filters */}
      <div style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '16px 20px', display: 'flex', gap: '28px', flexWrap: 'wrap', alignItems: 'center', boxShadow: '0 16px 40px rgba(3, 8, 20, 0.24)' }}>
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Risk Level</div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {RISK_FILTERS.map(r => (
              <button key={r} style={pillStyle(riskFilter === r)} onClick={() => { setRisk(r); setOffset(0) }}>{r}</button>
            ))}
          </div>
        </div>
        <div style={{ width: '1px', height: '36px', background: 'var(--border)' }} />
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Status</div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {STATUS_FILTERS.map(s => (
              <button key={s} style={pillStyle(statusFilter === s)} onClick={() => { setStatus(s as any); setOffset(0) }}>{s}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <ClaimsTable claims={claims} loading={loading} onAnalyze={handleAnalyze} />

      {/* Pagination */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', alignItems: 'center' }}>
        <button onClick={() => setOffset(o => Math.max(0, o - LIMIT))} disabled={offset === 0} className="btn-secondary" style={{ opacity: offset === 0 ? 0.4 : 1 }}>
          Previous
        </button>
        <span style={{ color: 'var(--muted)', fontSize: '0.8125rem' }}>Page {Math.floor(offset / LIMIT) + 1}</span>
        <button onClick={() => setOffset(o => o + LIMIT)} disabled={claims.length < LIMIT} className="btn-secondary" style={{ opacity: claims.length < LIMIT ? 0.4 : 1 }}>
          Next
        </button>
      </div>
    </div>
  )
}
