/**
 * RedTeamMode — demo panel to quickly load sample analysis results.
 * Lets judges/reviewers see all 4 risk levels without entering claim data.
 * Shows "Demo Mode" badge and scenario selector.
 */

import { useState } from 'react'
import type { InvestigatorReport } from '../types'
import { analysisApi } from '../lib/api'
import { MOCK_CRITICAL_REPORT, MOCK_LOW_REPORT } from '../lib/mockData'

interface Props {
  onReport: (report: InvestigatorReport) => void
}

type Scenario = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

const SCENARIOS: { key: Scenario; label: string; description: string; color: string }[] = [
  {
    key:         'CRITICAL',
    label:       'Fraud Ring',
    description: 'Coordinated multi-claimant ring · Score 91/100',
    color:       '#DC2626',
  },
  {
    key:         'HIGH',
    label:       'High Risk',
    description: 'Repeat claimant, multiple providers · Score 69/100',
    color:       '#EA580C',
  },
  {
    key:         'MEDIUM',
    label:       'Medium Risk',
    description: 'Elevated claim amount · Score 41/100',
    color:       '#D97706',
  },
  {
    key:         'LOW',
    label:       'Clean Claim',
    description: 'No red flags detected · Score 10/100',
    color:       '#16A34A',
  },
]

export function RedTeamMode({ onReport }: Props) {
  const [loading, setLoading]   = useState<Scenario | null>(null)
  const [expanded, setExpanded] = useState(true)

  const loadScenario = async (scenario: Scenario) => {
    setLoading(scenario)
    try {
      // Try real API first
      const report = await analysisApi.getDemo(scenario)
      onReport(report)
    } catch {
      // Fall back to mock data for offline demo
      if (scenario === 'CRITICAL') onReport(MOCK_CRITICAL_REPORT)
      else if (scenario === 'LOW')  onReport(MOCK_LOW_REPORT)
      else {
        // Generate a rough mock for MED/HIGH
        const mockReport: InvestigatorReport = {
          ...MOCK_CRITICAL_REPORT,
          claim_token:  `DEMO_${scenario}_001`,
          factsheet_id: `DEMO${scenario.slice(0,4)}`,
          narrative:    `Demo ${scenario} risk scenario loaded. Backend not connected — showing mock data.`,
          analysis: {
            ...MOCK_CRITICAL_REPORT.analysis,
            risk_level:     scenario,
            combined_score: scenario === 'HIGH' ? 69 : 41,
            gnn_score:      scenario === 'HIGH' ? 68 : 44,
            isolation_score:scenario === 'HIGH' ? 71 : 38,
          },
        }
        onReport(mockReport)
      }
    } finally {
      setLoading(null)
    }
  }

  return (
    <div style={{
      background:   'var(--panel)',
      border:       '1px solid var(--border)',
      borderRadius: '10px',
      overflow:     'hidden',
      boxShadow:    '0 16px 40px rgba(3, 8, 20, 0.24)',
    }}>
      {/* Header */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width:          '100%',
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'space-between',
          padding:        '14px 20px',
          background:     'transparent',
          border:         'none',
          cursor:         'pointer',
          borderBottom:   expanded ? '1px solid var(--border)' : 'none',
          fontFamily:     'Inter, sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text)' }}>Demo Scenarios</span>
          <span style={{
            background: 'var(--panel-soft)', border: '1px solid var(--border)',
            color: 'var(--muted)', fontSize: '0.7rem', fontWeight: 600,
            borderRadius: '9999px', padding: '2px 10px', letterSpacing: '0.05em',
          }}>
            RED TEAM
          </span>
        </div>
        <span style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && (
        <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          {SCENARIOS.map(s => (
            <button
              key={s.key}
              onClick={() => loadScenario(s.key)}
              disabled={loading !== null}
              style={{
                background:   'var(--panel-alt)',
                border:       `1px solid ${loading === s.key ? s.color : 'var(--border)'}`,
                borderRadius: '10px',
                padding:      '14px',
                textAlign:    'left',
                cursor:       loading !== null ? 'wait' : 'pointer',
                transition:   'all 0.2s ease',
                opacity:      loading !== null && loading !== s.key ? 0.5 : 1,
                fontFamily:   'Inter, sans-serif',
              }}
              onMouseEnter={e => !loading && (e.currentTarget.style.borderColor = s.color)}
              onMouseLeave={e => !loading && (e.currentTarget.style.borderColor = 'var(--border)')}
            >
              {/* Color dot + label */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                {loading === s.key ? (
                  <span style={{ color: s.color, fontSize: '0.875rem' }}>⟳</span>
                ) : (
                  <span style={{
                    width: '8px', height: '8px', borderRadius: '50%',
                    background: s.color, flexShrink: 0,
                    display: 'inline-block',
                  }} />
                )}
                <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text)' }}>
                  {s.label}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)', lineHeight: 1.4 }}>
                {s.description}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
