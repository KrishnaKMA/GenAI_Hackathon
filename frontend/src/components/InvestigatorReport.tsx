/**
 * InvestigatorReport — full analysis report panel.
 * Shows: scores, evidence list, SHAP features, narrative, graph.
 */

import { useState } from 'react'
import type { InvestigatorReport as Report } from '../types'
import { FraudScoreBadge } from './FraudScoreBadge'
import { FraudGraph } from './FraudGraph'
import { TimelineSlider } from './TimelineSlider'
import { AgentStatus } from './AgentStatus'
import { formatDateTime } from '../lib/utils'

interface Props {
  report: Report
}

type Tab = 'graph' | 'evidence' | 'shap' | 'narrative'

export function InvestigatorReport({ report }: Props) {
  const { analysis, claim_token, narrative, factsheet_id, generated_at } = report
  const [activeTab, setActiveTab]   = useState<Tab>('graph')
  const [filterDate, setFilterDate] = useState<string | undefined>()
  const [showAgent, setShowAgent]   = useState(analysis.combined_score >= 75)

  const tabs: { key: Tab; label: string }[] = [
    { key: 'graph',     label: 'Entity Graph' },
    { key: 'evidence',  label: 'GNN Evidence' },
    { key: 'shap',      label: 'SHAP Features' },
    { key: 'narrative', label: 'Narrative' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header row */}
      <div style={{
        background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '12px',
        padding: '20px 24px', boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: '16px',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1A1A1A' }}>
              Case {claim_token.slice(0, 12).toUpperCase()}
            </h2>
            <span style={{
              background: '#F0EFEB', border: '1px solid #E8E6E1',
              color: '#6B6B6B', fontSize: '0.7rem', fontWeight: 600,
              borderRadius: '9999px', padding: '2px 8px', letterSpacing: '0.05em',
            }}>
              #{factsheet_id}
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#9A9A9A' }}>
            Generated {formatDateTime(generated_at)}
          </div>
        </div>

        <FraudScoreBadge
          score={analysis.combined_score}
          riskLevel={analysis.risk_level}
          size="lg"
        />
      </div>

      {/* Score cards row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {[
          { label: 'GNN Score',       value: analysis.gnn_score,       sub: 'GraphSAGE network anomaly' },
          { label: 'Isolation Score', value: analysis.isolation_score,  sub: 'Statistical outlier score' },
          { label: 'Combined Score',  value: analysis.combined_score,   sub: 'Ensemble weighted output' },
        ].map(card => (
          <div key={card.label} style={{
            background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '12px',
            padding: '16px 20px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <div style={{ fontSize: '0.75rem', color: '#9A9A9A', marginBottom: '6px' }}>{card.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span style={{ fontSize: '2rem', fontWeight: 700, color: '#1A1A1A', lineHeight: 1 }}>
                {Math.round(card.value)}
              </span>
              <span style={{ fontSize: '0.875rem', color: '#9A9A9A' }}>/100</span>
            </div>

            {/* Score bar */}
            <div style={{ marginTop: '10px', height: '4px', background: '#E8E6E1', borderRadius: '2px' }}>
              <div style={{
                width:        `${card.value}%`,
                height:       '100%',
                borderRadius: '2px',
                background:   card.value >= 85 ? '#DC2626' : card.value >= 60 ? '#EA580C' : card.value >= 35 ? '#D97706' : '#16A34A',
                transition:   'width 0.6s ease',
              }} />
            </div>

            <div style={{ fontSize: '0.7rem', color: '#9A9A9A', marginTop: '6px' }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        {/* Tab bar */}
        <div style={{
          display: 'flex', borderBottom: '1px solid #E8E6E1',
          background: '#F7F6F3',
        }}>
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                flex:         1,
                padding:      '12px 16px',
                background:   activeTab === tab.key ? '#FFFFFF' : 'transparent',
                border:       'none',
                borderBottom: activeTab === tab.key ? '2px solid #1A1A1A' : '2px solid transparent',
                color:        activeTab === tab.key ? '#1A1A1A' : '#9A9A9A',
                fontSize:     '0.8125rem',
                fontWeight:   activeTab === tab.key ? 600 : 400,
                cursor:       'pointer',
                transition:   'all 0.15s ease',
                fontFamily:   'Inter, sans-serif',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ padding: '0' }}>

          {/* GRAPH TAB */}
          {activeTab === 'graph' && (
            <div style={{ padding: '16px' }}>
              <div style={{ height: '420px', marginBottom: '16px' }}>
                <FraudGraph
                  nodes={analysis.graph_nodes}
                  edges={analysis.graph_edges}
                  evidence={analysis.gnn_evidence}
                  filterDate={filterDate}
                />
              </div>
              <TimelineSlider
                edges={analysis.graph_edges}
                onChange={setFilterDate}
              />
            </div>
          )}

          {/* EVIDENCE TAB */}
          {activeTab === 'evidence' && (
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <p style={{ fontSize: '0.8125rem', color: '#9A9A9A', marginBottom: '4px' }}>
                GNNExplainer identified these graph edges as most predictive of fraud.
              </p>
              {analysis.gnn_evidence.map((ev, i) => (
                <div key={i} style={{
                  background: '#F7F6F3', border: '1px solid #E8E6E1', borderRadius: '10px',
                  padding: '14px 16px',
                  borderLeft: `3px solid ${ev.importance_score >= 0.8 ? '#DC2626' : ev.importance_score >= 0.6 ? '#D97706' : '#6B6B6B'}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#1A1A1A', marginBottom: '4px' }}>
                        {ev.human_label}
                      </div>
                      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.7rem', color: '#9A9A9A' }}>
                          {ev.source_token.slice(0, 12)} → {ev.target_token.slice(0, 12)}
                        </span>
                        <span style={{
                          fontSize: '0.7rem', color: '#6B6B6B',
                          background: '#F0EFEB', borderRadius: '4px', padding: '1px 6px',
                        }}>
                          {ev.edge_type}
                        </span>
                      </div>
                    </div>
                    {/* Importance bar */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', flexShrink: 0 }}>
                      <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#1A1A1A' }}>
                        {Math.round(ev.importance_score * 100)}%
                      </span>
                      <div style={{ width: '80px', height: '4px', background: '#E8E6E1', borderRadius: '2px' }}>
                        <div style={{
                          width: `${ev.importance_score * 100}%`, height: '100%', borderRadius: '2px',
                          background: ev.importance_score >= 0.8 ? '#DC2626' : ev.importance_score >= 0.6 ? '#D97706' : '#6B6B6B',
                        }} />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* SHAP TAB */}
          {activeTab === 'shap' && (
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <p style={{ fontSize: '0.8125rem', color: '#9A9A9A', marginBottom: '4px' }}>
                SHAP attributions explain the Isolation Forest's anomaly score.
              </p>
              {analysis.shap_features.map((feat, i) => (
                <div key={i} style={{
                  background: '#F7F6F3', border: '1px solid #E8E6E1', borderRadius: '10px',
                  padding: '12px 16px',
                  display: 'flex', alignItems: 'center', gap: '12px',
                }}>
                  {/* Direction arrow */}
                  <span style={{
                    fontSize: '1.1rem',
                    color: feat.direction === 'increases_risk' ? '#DC2626' : '#16A34A',
                    flexShrink: 0,
                  }}>
                    {feat.direction === 'increases_risk' ? '↑' : '↓'}
                  </span>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#1A1A1A' }}>
                        {feat.feature_name.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: '#6B6B6B', fontWeight: 600 }}>
                        {feat.value}
                      </span>
                    </div>
                    {/* SHAP bar */}
                    <div style={{ height: '6px', background: '#E8E6E1', borderRadius: '3px' }}>
                      <div style={{
                        width: `${feat.contribution * 100}%`, height: '100%', borderRadius: '3px',
                        background: feat.direction === 'increases_risk' ? '#DC2626' : '#16A34A',
                        transition: 'width 0.5s ease',
                      }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                      <span style={{ fontSize: '0.7rem', color: '#9A9A9A' }}>contribution</span>
                      <span style={{
                        fontSize: '0.7rem', fontWeight: 600,
                        color: feat.direction === 'increases_risk' ? '#DC2626' : '#16A34A',
                      }}>
                        {Math.round(feat.contribution * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* NARRATIVE TAB */}
          {activeTab === 'narrative' && (
            <div style={{ padding: '20px 24px' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px',
              }}>
                <span style={{ fontSize: '0.8125rem', color: '#9A9A9A' }}>
                  Generated by IBM Granite LLM
                </span>
                <span style={{
                  background: '#F0EFEB', border: '1px solid #E8E6E1',
                  color: '#6B6B6B', fontSize: '0.7rem', borderRadius: '4px', padding: '2px 8px',
                }}>
                  AI-Generated
                </span>
              </div>
              <div style={{
                whiteSpace: 'pre-line',
                fontSize:   '0.875rem',
                lineHeight: '1.7',
                color:      '#6B6B6B',
              }}>
                {narrative}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Agent Status Panel (auto-shows for HIGH/CRITICAL) */}
      {analysis.combined_score >= 75 && (
        <AgentStatus claimToken={claim_token} analysis={analysis} />
      )}
    </div>
  )
}
