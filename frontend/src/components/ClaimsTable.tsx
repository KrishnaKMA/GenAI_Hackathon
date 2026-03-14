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
  pending:  { color: '#9A9A9A', label: 'Pending'  },
  analyzed: { color: '#6B6B6B', label: 'Analyzed' },
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
      <div style={{ background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '12px', padding: '40px', textAlign: 'center', color: '#9A9A9A', fontSize: '0.875rem', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        No claims found. Submit a claim to get started.
      </div>
    )
  }

  return (
    <div style={{ background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#F7F6F3', borderBottom: '1px solid #E8E6E1' }}>
            {['Token', 'Amount', 'Type', 'Status', 'Risk', 'Score', 'Filed', 'Actions'].map(h => (
              <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 600, color: '#9A9A9A', letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
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
                style={{ borderBottom: '1px solid #F0EFEB', cursor: claim.combined_score != null ? 'pointer' : 'default', transition: 'background 0.12s ease' }}
                onMouseEnter={e => (e.currentTarget.style.background = '#F7F6F3')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#6B6B6B', fontWeight: 500 }}>
                    {claim.claim_token.slice(0, 14).toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.875rem', color: '#1A1A1A', fontWeight: 600 }}>
                  {formatCurrency(claim.claim_amount)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ background: '#F0EFEB', borderRadius: '6px', padding: '3px 8px', fontSize: '0.75rem', color: '#6B6B6B' }}>
                    {claim.claim_type.replace('_', ' ')}
                  </span>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ fontSize: '0.75rem', color: statusInfo.color, fontWeight: 500 }}>● {statusInfo.label}</span>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {claim.risk_level ? <RiskChip riskLevel={claim.risk_level} /> : (
                    <span style={{ color: '#C4C4C4', fontSize: '0.75rem' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {claim.combined_score != null ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#1A1A1A' }}>{Math.round(claim.combined_score)}</span>
                      <div style={{ width: '48px', height: '3px', background: '#E8E6E1', borderRadius: '2px' }}>
                        <div style={{ width: `${claim.combined_score}%`, height: '100%', borderRadius: '2px', background: claim.combined_score >= 85 ? '#DC2626' : claim.combined_score >= 60 ? '#EA580C' : claim.combined_score >= 35 ? '#D97706' : '#16A34A' }} />
                      </div>
                    </div>
                  ) : (
                    <span style={{ color: '#C4C4C4', fontSize: '0.75rem' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: '#9A9A9A', whiteSpace: 'nowrap' }}>
                  {formatDate(claim.filing_date)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {claim.status === 'pending' && onAnalyze && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onAnalyze(claim.claim_token) }}
                      style={{ background: '#1A1A1A', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, padding: '5px 12px', cursor: 'pointer', transition: 'background 0.12s ease', fontFamily: 'Inter, sans-serif' }}
                      onMouseEnter={e => (e.currentTarget.style.background = '#2D2D2D')}
                      onMouseLeave={e => (e.currentTarget.style.background = '#1A1A1A')}
                    >
                      Analyze
                    </button>
                  )}
                  {claim.combined_score != null && (
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/report/${claim.claim_token}`) }}
                      style={{ background: 'transparent', color: '#6B6B6B', border: '1px solid #E8E6E1', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 500, padding: '5px 12px', cursor: 'pointer', transition: 'all 0.12s ease', fontFamily: 'Inter, sans-serif' }}
                      onMouseEnter={e => { e.currentTarget.style.background = '#F0EFEB'; e.currentTarget.style.color = '#1A1A1A' }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#6B6B6B' }}
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
