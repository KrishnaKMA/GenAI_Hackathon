import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ClaimInput } from '../types'
import { claimsApi, analysisApi } from '../lib/api'

export function SubmitClaimPage() {
  const navigate = useNavigate()
  const user     = JSON.parse(localStorage.getItem('cs_user') || '{}')

  const [form, setForm] = useState<ClaimInput>({
    claimant_name:         '',
    provider_name:         '',
    repair_shop_name:      '',
    claim_amount:          0,
    claim_type:            'auto_repair',
    incident_date:         '',
    filing_date:           new Date().toISOString().slice(0, 10),
    prior_claim_count:     0,
    days_since_last_claim: undefined,
    adjuster_id:           user.username || '',
  })

  const [loading, setLoading]       = useState(false)
  const [analyzing, setAnalyzing]   = useState(false)
  const [error, setError]           = useState('')
  const [claimToken, setClaimToken] = useState('')

  const set = (field: keyof ClaimInput, value: any) =>
    setForm(f => ({ ...f, [field]: value }))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const record = await claimsApi.create(form)
      setClaimToken(record.claim_token)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit claim')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setError('')
    try {
      const report = await analysisApi.analyze(claimToken)
      if (report?.claim_token) {
        navigate(`/report/${claimToken}`)
        return
      }
      navigate(`/report/${claimToken}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to analyze claim')
    } finally {
      setAnalyzing(false)
    }
  }

  const inp: React.CSSProperties = {
    background: 'var(--panel-alt)', border: '1px solid var(--border)', borderRadius: '8px',
    padding: '9px 12px', color: 'var(--text)', fontSize: '0.875rem',
    width: '100%', outline: 'none', fontFamily: 'Inter, sans-serif',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
  }

  const lbl: React.CSSProperties = {
    display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted)',
    marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.06em',
  }

  const focus = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    e.target.style.borderColor = '#57B7F8'
    e.target.style.boxShadow   = '0 0 0 3px rgba(87,183,248,0.16)'
  }
  const blur = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    e.target.style.borderColor = 'var(--border)'
    e.target.style.boxShadow   = 'none'
  }

  return (
    <div style={{ maxWidth: '680px', margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <button onClick={() => navigate('/dashboard')} style={{ background: 'transparent', border: 'none', color: 'var(--muted)', fontSize: '0.8125rem', padding: 0, cursor: 'pointer', marginBottom: '10px', fontFamily: 'Inter, sans-serif' }}>
          ← Back to Dashboard
        </button>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Submit New Claim</h1>
        <p style={{ color: '#9A9A9A', fontSize: '0.8125rem', marginTop: '3px' }}>Personal data is tokenized before storage — no PII is retained.</p>
      </div>

      {claimToken ? (
        <div style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '32px', textAlign: 'center', boxShadow: '0 16px 40px rgba(3, 8, 20, 0.24)' }}>
          <div style={{ width: '48px', height: '48px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: '#16A34A', fontWeight: 700, fontSize: '1.25rem' }}>✓</div>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text)', marginBottom: '8px' }}>Claim Submitted</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '4px' }}>
            Token: <span style={{ fontFamily: 'monospace', color: 'var(--text)', fontWeight: 600 }}>{claimToken}</span>
          </p>
          <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '24px' }}>PII has been tokenized. Run analysis to detect fraud patterns.</p>
          {error && (
            <div style={{ background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: '8px', padding: '10px 14px', color: '#DC2626', fontSize: '0.8125rem', marginBottom: '16px' }}>{error}</div>
          )}
          <button onClick={handleAnalyze} disabled={analyzing} className="btn-primary" style={{ minWidth: '200px', opacity: analyzing ? 0.6 : 1 }}>
            {analyzing ? 'Running analysis...' : 'Analyze for Fraud'}
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '28px', display: 'flex', flexDirection: 'column', gap: '18px', boxShadow: '0 16px 40px rgba(3, 8, 20, 0.24)' }}>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={lbl}>Claimant Name *</label>
              <input style={inp} placeholder="Full name" value={form.claimant_name} onChange={e => set('claimant_name', e.target.value)} required onFocus={focus} onBlur={blur} />
            </div>
            <div>
              <label style={lbl}>Provider Name *</label>
              <input style={inp} placeholder="Hospital or clinic" value={form.provider_name} onChange={e => set('provider_name', e.target.value)} required onFocus={focus} onBlur={blur} />
            </div>
          </div>

          <div>
            <label style={lbl}>Repair Shop (if applicable)</label>
            <input style={inp} placeholder="Shop name" value={form.repair_shop_name || ''} onChange={e => set('repair_shop_name', e.target.value)} onFocus={focus} onBlur={blur} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={lbl}>Claim Amount (CAD) *</label>
              <input type="number" min={1} style={inp} placeholder="50000" value={form.claim_amount || ''} onChange={e => set('claim_amount', parseFloat(e.target.value))} required onFocus={focus} onBlur={blur} />
            </div>
            <div>
              <label style={lbl}>Claim Type *</label>
              <select style={{ ...inp, cursor: 'pointer' }} value={form.claim_type} onChange={e => set('claim_type', e.target.value)} onFocus={focus} onBlur={blur}>
                <option value="auto_repair">Auto Repair</option>
                <option value="medical">Medical</option>
                <option value="property">Property</option>
                <option value="liability">Liability</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={lbl}>Incident Date *</label>
              <input type="date" style={inp} value={form.incident_date} onChange={e => set('incident_date', e.target.value)} required onFocus={focus} onBlur={blur} />
            </div>
            <div>
              <label style={lbl}>Filing Date *</label>
              <input type="date" style={inp} value={form.filing_date} onChange={e => set('filing_date', e.target.value)} required onFocus={focus} onBlur={blur} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={lbl}>Prior Claims (last 5 years)</label>
              <input type="number" min={0} style={inp} value={form.prior_claim_count} onChange={e => set('prior_claim_count', parseInt(e.target.value) || 0)} onFocus={focus} onBlur={blur} />
            </div>
            <div>
              <label style={lbl}>Days Since Last Claim</label>
              <input type="number" min={0} style={inp} placeholder="Leave blank if first claim" value={form.days_since_last_claim || ''} onChange={e => set('days_since_last_claim', e.target.value ? parseInt(e.target.value) : undefined)} onFocus={focus} onBlur={blur} />
            </div>
          </div>

          {error && (
            <div style={{ background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: '8px', padding: '10px 14px', color: '#DC2626', fontSize: '0.8125rem' }}>{error}</div>
          )}

          <div style={{ background: 'var(--panel-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px 14px', fontSize: '0.75rem', color: 'var(--muted)' }}>
            Claimant name and provider name are encrypted and tokenized before storage. Only anonymized tokens appear in the fraud graph.
          </div>

          <button type="submit" disabled={loading} className="btn-primary" style={{ width: '100%', opacity: loading ? 0.6 : 1 }}>
            {loading ? 'Submitting...' : 'Submit Claim'}
          </button>
        </form>
      )}
    </div>
  )
}
