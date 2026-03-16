import { useEffect, useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import type { InvestigatorReport } from '../types'
import { analysisApi, cacheReport, getCachedReport } from '../lib/api'
import { InvestigatorReport as ReportComponent } from '../components/InvestigatorReport'
import { MOCK_CRITICAL_REPORT } from '../lib/mockData'

export function ReportPage() {
  const { claimToken }  = useParams<{ claimToken: string }>()
  const [searchParams]  = useSearchParams()
  const navigate        = useNavigate()
  const isDemo          = searchParams.get('demo') === '1'
  const forceRefresh    = searchParams.get('refresh') === '1'

  const [report, setReport]   = useState<InvestigatorReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const cachedReport = !forceRefresh && claimToken ? getCachedReport(claimToken) : null
      if (cachedReport && !isDemo) {
        setReport(cachedReport)
      }

      setLoading(true)
      setError('')
      try {
        if (isDemo) {
          const stored = sessionStorage.getItem('demo_report')
          if (stored) {
            if (!cancelled) setReport(JSON.parse(stored))
            return
          }
        }
        if (!claimToken) return
        const result = await analysisApi.analyze(claimToken)
        cacheReport(result)
        if (!cancelled) setReport(result)
      } catch (err: any) {
        console.warn('[ReportPage] API error, using fallback:', err?.message)
        if (!cancelled) {
          if (cachedReport && !isDemo) {
            setError('Showing cached report because the latest analysis request failed.')
          } else {
            setReport(MOCK_CRITICAL_REPORT)
            setError('Latest analysis could not be loaded. Showing fallback report.')
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [claimToken, forceRefresh, isDemo])

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

      {loading && !report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="skeleton" style={{ height: '80px', borderRadius: '12px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
            {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: '100px', borderRadius: '12px' }} />)}
          </div>
          <div className="skeleton" style={{ height: '420px', borderRadius: '12px' }} />
        </div>
      )}

      {error && (
        <div style={{ background: 'rgba(127, 29, 29, 0.22)', border: '1px solid rgba(248, 113, 113, 0.35)', borderRadius: '12px', padding: '16px 20px', color: '#FCA5A5' }}>{error}</div>
      )}

      {report && !loading && <ReportComponent report={report} />}
      {report && loading && <ReportComponent report={report} />}
    </div>
  )
}
