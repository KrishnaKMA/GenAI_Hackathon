import { useNavigate } from 'react-router-dom'
import type { ClaimRecord } from '../types'
import { RiskChip } from './FraudScoreBadge'
import { formatCurrency, formatDate } from '../lib/utils'

interface Props {
  claims: ClaimRecord[]
  loading?: boolean
  onAnalyze?: (token: string) => void
}

const STATUS_COLORS: Record<string, { color: string; label: string }> = {
  pending:  { color: 'var(--muted)', label: 'Pending'  },
  analyzed: { color: 'var(--muted)', label: 'Analyzed' },
  flagged:  { color: '#DC2626', label: 'Flagged'  },
  approved: { color: '#16A34A', label: 'Approved' },
  rejected: { color: '#EA580C', label: 'Rejected' },
}

export function ClaimsTable({ claims, loading, onAnalyze }: Props) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: '52px', borderRadius: '8px' }} />
        ))}
      </div>
    )
  }

  if (claims.length === 0) {
    return (
      <div style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '12px', padding: '40px', textAlign: 'center', color: 'var(--muted)', fontSize: '0.875rem', boxShadow: '0 16px 40px rgba(3, 8, 20, 0.24)' }}>
        No claims found. Submit a claim to get started.
      </div>
    )
  }

  return (
    <div style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 16px 40px rgba(3, 8, 20, 0.24)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: 'var(--panel-alt)', borderBottom: '1px solid var(--border)' }}>
            {['Token', 'Amount', 'Type', 'Status', 'Risk', 'Score', 'Filed', 'Actions'].map(h => (
              <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted)', letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => {
            const statusInfo = STATUS_COLORS[claim.status] || STATUS_COLORS.pending
            return (
              <tr
                key={claim.claim_token}
                onClick={() => claim.combined_score != null && navigate(`/report/${claim.claim_token}`)}
                style={{ borderBottom: '1px solid var(--border)', cursor: claim.combined_score != null ? 'pointer' : 'default', transition: 'background 0.12s ease' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(41, 59, 105, 0.22)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text)', fontWeight: 500 }}>
                    {claim.claim_token.slice(0, 14).toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.875rem', color: 'var(--text)', fontWeight: 600 }}>
                  {formatCurrency(claim.claim_amount)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ background: 'var(--panel-soft)', border: '1px solid var(--border)', borderRadius: '999px', padding: '3px 8px', fontSize: '0.75rem', color: 'var(--muted)' }}>
                    {claim.claim_type.replace('_', ' ')}
                  </span>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ fontSize: '0.75rem', color: statusInfo.color, fontWeight: 500 }}>● {statusInfo.label}</span>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {claim.risk_level ? <RiskChip riskLevel={claim.risk_level} /> : (
                    <span style={{ color: 'var(--subtle)', fontSize: '0.75rem' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {claim.combined_score != null ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text)' }}>{Math.round(claim.combined_score)}</span>
                      <div style={{ width: '48px', height: '3px', background: 'rgba(255,255,255,0.12)', borderRadius: '2px' }}>
                        <div style={{ width: `${claim.combined_score}%`, height: '100%', borderRadius: '2px', background: claim.combined_score >= 85 ? '#DC2626' : claim.combined_score >= 60 ? '#EA580C' : claim.combined_score >= 35 ? '#D97706' : '#16A34A' }} />
                      </div>
                    </div>
                  ) : (
                    <span style={{ color: 'var(--subtle)', fontSize: '0.75rem' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                  {formatDate(claim.filing_date)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {claim.status === 'pending' && onAnalyze && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onAnalyze(claim.claim_token) }}
                      style={{ background: 'linear-gradient(135deg, #57B7F8, #4B7CF4)', color: '#08111f', border: 'none', borderRadius: '8px', fontSize: '0.75rem', fontWeight: 700, padding: '6px 12px', cursor: 'pointer', transition: 'filter 0.12s ease', fontFamily: 'Inter, sans-serif' }}
                      onMouseEnter={e => (e.currentTarget.style.filter = 'brightness(1.06)')}
                      onMouseLeave={e => (e.currentTarget.style.filter = 'brightness(1)')}
                    >
                      Analyze
                    </button>
                  )}
                  {claim.combined_score != null && (
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/report/${claim.claim_token}`) }}
                      style={{ background: 'transparent', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '0.75rem', fontWeight: 600, padding: '6px 12px', cursor: 'pointer', transition: 'all 0.12s ease', fontFamily: 'Inter, sans-serif' }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = 'var(--text)' }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text)' }}
                    >
                      View
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
