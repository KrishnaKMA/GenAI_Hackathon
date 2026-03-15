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
        <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text)' }}>
          IBM watsonx.governance
        </h3>
        <span style={{
          background: 'var(--panel-soft)', border: '1px solid var(--border)',
          color: 'var(--muted)', fontSize: '0.7rem', borderRadius: '999px', padding: '2px 8px',
        }}>
          AI Audit Trail
        </span>
      </div>

      {entries.length === 0 && (
        <div style={{
          background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: '10px',
          padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: '0.875rem',
        }}>
          No factsheet entries yet. Run an analysis to generate one.
        </div>
      )}

      {entries.map((entry) => (
        <div
          key={entry.factsheet_id}
          style={{
            background:   'var(--panel)',
            border:       '1px solid var(--border)',
            borderRadius: '10px',
            padding:      '14px 16px',
            borderLeft:   `3px solid ${entry.decision === 'FLAGGED' ? '#DC2626' : '#16A34A'}`,
            transition:   'all 0.15s ease',
            boxShadow:    '0 12px 32px rgba(3, 8, 20, 0.18)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            {/* Left: tokens */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontFamily: 'monospace', fontSize: '0.8125rem',
                  color: 'var(--text)', fontWeight: 600,
                }}>
                  #{entry.factsheet_id}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--subtle)' }}>·</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                  {entry.claim_token.slice(0, 14).toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--subtle)' }}>
                {formatDateTime(entry.timestamp)} · {entry.model_version}
              </div>
            </div>

            {/* Right: score + decision */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <RiskChip riskLevel={entry.risk_level as any} />

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>
                  {Math.round(entry.combined_score)}<span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>/100</span>
                </div>
              </div>

              <span style={{
                background:    entry.decision === 'FLAGGED' ? 'rgba(220, 38, 38, 0.14)' : 'rgba(22, 163, 74, 0.14)',
                border:        `1px solid ${entry.decision === 'FLAGGED' ? 'rgba(248, 113, 113, 0.35)' : 'rgba(74, 222, 128, 0.35)'}`,
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
          <div style={{ marginTop: '8px', fontSize: '0.7rem', color: 'var(--subtle)' }}>
            Adjuster: {entry.adjuster_id}
          </div>
        </div>
      ))}
    </div>
  )
}
