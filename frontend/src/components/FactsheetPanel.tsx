/**
 * FactsheetPanel — IBM watsonx.governance AI audit trail.
 * Shows model decisions for each claim: score, risk, decision, adjuster.
 * In mock mode: reads from local JSON file.
 * In real mode (Teammate B): reads from watsonx.governance API.
 */

import type { FactsheetEntry } from '../types'
import { RiskChip } from './FraudScoreBadge'
import { formatDateTime } from '../lib/utils'

interface Props {
  entries: FactsheetEntry[]
  loading?: boolean
}

export function FactsheetPanel({ entries, loading }: Props) {
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: '72px', borderRadius: '10px' }} />
        ))}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
        <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#1A1A1A' }}>
          IBM watsonx.governance
        </h3>
        <span style={{
          background: '#F0EFEB', border: '1px solid #E8E6E1',
          color: '#9A9A9A', fontSize: '0.7rem', borderRadius: '4px', padding: '2px 8px',
        }}>
          AI Audit Trail
        </span>
      </div>

      {entries.length === 0 && (
        <div style={{
          background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '10px',
          padding: '24px', textAlign: 'center', color: '#9A9A9A', fontSize: '0.875rem',
        }}>
          No factsheet entries yet. Run an analysis to generate one.
        </div>
      )}

      {entries.map((entry) => (
        <div
          key={entry.factsheet_id}
          style={{
            background:   '#FFFFFF',
            border:       '1px solid #E8E6E1',
            borderRadius: '10px',
            padding:      '14px 16px',
            borderLeft:   `3px solid ${entry.decision === 'FLAGGED' ? '#DC2626' : '#16A34A'}`,
            transition:   'all 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            {/* Left: tokens */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontFamily: 'monospace', fontSize: '0.8125rem',
                  color: '#6B6B6B', fontWeight: 600,
                }}>
                  #{entry.factsheet_id}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#C4C4C4' }}>·</span>
                <span style={{ fontSize: '0.75rem', color: '#9A9A9A' }}>
                  {entry.claim_token.slice(0, 14).toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#C4C4C4' }}>
                {formatDateTime(entry.timestamp)} · {entry.model_version}
              </div>
            </div>

            {/* Right: score + decision */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <RiskChip riskLevel={entry.risk_level as any} />

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1A1A1A', lineHeight: 1 }}>
                  {Math.round(entry.combined_score)}<span style={{ fontSize: '0.75rem', color: '#9A9A9A' }}>/100</span>
                </div>
              </div>

              <span style={{
                background:    entry.decision === 'FLAGGED' ? '#FEE2E2' : '#F0FDF4',
                border:        `1px solid ${entry.decision === 'FLAGGED' ? '#FECACA' : '#BBF7D0'}`,
                color:         entry.decision === 'FLAGGED' ? '#DC2626' : '#16A34A',
                borderRadius:  '9999px',
                padding:       '3px 10px',
                fontSize:      '0.75rem',
                fontWeight:    600,
                letterSpacing: '0.04em',
              }}>
                {entry.decision}
              </span>
            </div>
          </div>

          {/* Footer */}
          <div style={{ marginTop: '8px', fontSize: '0.7rem', color: '#C4C4C4' }}>
            Adjuster: {entry.adjuster_id}
          </div>
        </div>
      ))}
    </div>
  )
}
