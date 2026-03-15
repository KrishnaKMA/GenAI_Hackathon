import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ClaimRecord, InvestigatorReport, FactsheetEntry } from '../types'
import { claimsApi, adminApi, analysisApi, cacheReport } from '../lib/api'
import { MOCK_CLAIMS, MOCK_FACTSHEETS } from '../lib/mockData'
import { ClaimsTable } from '../components/ClaimsTable'
import { FactsheetPanel } from '../components/FactsheetPanel'
import { RedTeamMode } from '../components/RedTeamMode'

interface Stats {
  total_claims: number
  flagged: number
  approved: number
  pending: number
  critical: number
}

function StatCard({ label, value, loading }: { label: string; value: number; loading: boolean }) {
  return (
    <div style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 16px 40px rgba(3, 8, 20, 0.32)' }}>
      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
        {label}
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text)', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
        {loading ? '—' : value}
      </div>
    </div>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [claims, setClaims]       = useState<ClaimRecord[]>([])
  const [sheets, setSheets]       = useState<FactsheetEntry[]>([])
  const [stats, setStats]         = useState<Stats | null>(null)
  const [loading, setLoading]     = useState(true)
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  const user = JSON.parse(localStorage.getItem('cs_user') || '{}')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const requests: Promise<unknown>[] = [
          claimsApi.list({ limit: 20, offset: 0 }),
          claimsApi.getFactsheets(10),
        ]
        if (user.role === 'admin') {
          requests.push(adminApi.getStats())
        }
        const [claimsData, sheetsData, statsData] = await Promise.all(requests)
        if (cancelled) return
        setClaims(claimsData as ClaimRecord[])
        setSheets(sheetsData as FactsheetEntry[])
        if (statsData) {
          setStats(statsData as Stats)
        }
      } catch {
        if (cancelled) return
        if (claims.length === 0) setClaims(MOCK_CLAIMS)
        if (sheets.length === 0) setSheets(MOCK_FACTSHEETS)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const handleAnalyze = async (token: string) => {
    setAnalyzing(token)
    try {
      const report = await analysisApi.analyze(token)
      cacheReport(report)
      const refreshed = await claimsApi.list({ limit: 20, offset: 0 })
      setClaims(refreshed)
    } catch {
      setClaims(prev => prev.map(c => c.claim_token === token ? { ...c, status: 'analyzed' } : c))
    } finally {
      setAnalyzing(null)
    }
  }

  const handleDemoReport = (report: InvestigatorReport) => {
    sessionStorage.setItem('demo_report', JSON.stringify(report))
    navigate(`/report/${report.claim_token}?demo=1`)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Dashboard</h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.8125rem', marginTop: '2px' }}>Welcome back, {user.username}</p>
        </div>
        <button onClick={() => navigate('/claims/new')} className="btn-primary">+ Submit Claim</button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        <StatCard label="Total Claims"  value={stats?.total_claims ?? claims.length}                                        loading={loading} />
        <StatCard label="Flagged"       value={stats?.flagged      ?? claims.filter(c => c.status === 'flagged').length}    loading={loading} />
        <StatCard label="Critical Risk" value={stats?.critical     ?? claims.filter(c => c.risk_level === 'CRITICAL').length} loading={loading} />
        <StatCard label="Approved"      value={stats?.approved     ?? claims.filter(c => c.status === 'approved').length}   loading={loading} />
      </div>

      {/* Demo panel */}
      <RedTeamMode onReport={handleDemoReport} />

      {/* Main content */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '20px', alignItems: 'start' }}>
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
            Recent Claims
          </div>
          <ClaimsTable claims={claims} loading={loading} onAnalyze={handleAnalyze} />
        </div>
        <FactsheetPanel entries={sheets} loading={loading} />
      </div>
    </div>
  )
}
