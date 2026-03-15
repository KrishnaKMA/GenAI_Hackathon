import { useEffect, useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import type { InvestigatorReport } from '../types'
import { analysisApi } from '../lib/api'
import { InvestigatorReport as ReportComponent } from '../components/InvestigatorReport'
import { MOCK_CRITICAL_REPORT } from '../lib/mockData'

export function ReportPage() {
  const { claimToken }  = useParams<{ claimToken: string }>()
  const [searchParams]  = useSearchParams()
  const navigate        = useNavigate()
  const isDemo          = searchParams.get('demo') === '1'

  const [report, setReport]   = useState<InvestigatorReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        if (isDemo) {
          const stored = sessionStorage.getItem('demo_report')
          if (stored) { setReport(JSON.parse(stored)); return }
        }
        if (!claimToken) return
        const result = await analysisApi.analyze(claimToken)
        setReport(result)
      } catch (err: any) {
        console.warn('[ReportPage] API error, using mock:', err?.message)
        setReport(MOCK_CRITICAL_REPORT)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [claimToken, isDemo])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Nav */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button onClick={() => navigate(-1)} style={{ background: 'transparent', border: 'none', color: 'var(--muted)', fontSize: '0.8125rem', padding: 0, cursor: 'pointer', fontFamily: 'Inter, sans-serif' }}>
          ← Back
        </button>
        <h1 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>Investigator Report</h1>
        {isDemo && (
          <span style={{ background: 'var(--panel-soft)', border: '1px solid var(--border)', color: 'var(--muted)', fontSize: '0.7rem', fontWeight: 600, borderRadius: '9999px', padding: '2px 10px', letterSpacing: '0.05em' }}>
            DEMO
          </span>
        )}
      </div>

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="skeleton" style={{ height: '80px', borderRadius: '12px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
            {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: '100px', borderRadius: '12px' }} />)}
          </div>
          <div className="skeleton" style={{ height: '420px', borderRadius: '12px' }} />
        </div>
      )}

      {error && !loading && (
        <div style={{ background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: '12px', padding: '20px', color: '#DC2626' }}>{error}</div>
      )}

      {report && !loading && <ReportComponent report={report} />}
    </div>
  )
}
