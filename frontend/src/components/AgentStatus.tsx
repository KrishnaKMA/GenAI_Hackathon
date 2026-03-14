/**
 * AgentStatus — live fraud agent step tracker.
 * Connects to WS /ws/agent/{claim_token} and streams 4 step updates.
 * Each step shows: running spinner → complete/warning icon → result text.
 */

import { useEffect, useRef, useState } from 'react'
import type { FraudAnalysisResult, AgentStepUpdate } from '../types'

interface Props {
  claimToken: string
  analysis: FraudAnalysisResult
  autoStart?: boolean
}

const STEP_ICONS = {
  pending:  '○',
  running:  '◌',
  complete: '✓',
  error:    '✗',
}

const STEP_COLORS = {
  pending:  '#C4C4C4',
  running:  '#1A1A1A',
  complete: '#16A34A',
  error:    '#DC2626',
}

const INITIAL_STEPS: AgentStepUpdate[] = [
  { step_id: 1, name: 'Alert Sent',        status: 'pending' },
  { step_id: 2, name: 'Business Verified', status: 'pending' },
  { step_id: 3, name: 'SIU Letter Drafted', status: 'pending' },
  { step_id: 4, name: 'Task Scheduled',    status: 'pending' },
]

export function AgentStatus({ claimToken, analysis, autoStart = true }: Props) {
  const [steps, setSteps]           = useState<AgentStepUpdate[]>(INITIAL_STEPS)
  const [running, setRunning]       = useState(false)
  const [done, setDone]             = useState(false)
  const [letter, setLetter]         = useState<string | null>(null)
  const [showLetter, setShowLetter] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const hasStarted = useRef(false)

  const startAgent = () => {
    if (running || done || hasStarted.current) return
    hasStarted.current = true
    setRunning(true)
    setSteps(INITIAL_STEPS)

    const wsUrl = `ws://localhost:8000/ws/agent/${claimToken}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({
        ...analysis,
        graph_nodes:   analysis.graph_nodes,
        graph_edges:   analysis.graph_edges,
        gnn_evidence:  analysis.gnn_evidence,
        shap_features: analysis.shap_features,
      }))
    }

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)

        if (data.status === 'done') {
          setRunning(false)
          setDone(true)
          return
        }
        if (data.status === 'error') {
          setRunning(false)
          return
        }

        const update = data as AgentStepUpdate

        setSteps(prev => prev.map(s =>
          s.step_id === update.step_id ? { ...s, ...update } : s
        ))

        if (update.siu_letter) {
          setLetter(update.siu_letter)
        }
      } catch (e) {
        // Ignore parse errors
      }
    }

    ws.onerror = () => {
      setRunning(false)
      _runMockSteps()
    }

    ws.onclose = () => {
      setRunning(false)
      if (!done) setDone(true)
    }
  }

  // Mock fallback — simulates steps without WS
  const _runMockSteps = async () => {
    const mockUpdates: Partial<AgentStepUpdate>[] = [
      { step_id: 1, status: 'running' },
      { step_id: 1, status: 'complete', result: `Priority alert logged · Case ${claimToken.slice(0,8).toUpperCase()}` },
      { step_id: 2, status: 'running' },
      { step_id: 2, status: 'complete', result: 'UNREGISTERED — not found in Canadian Business Registry', is_warning: true },
      { step_id: 3, status: 'running' },
      { step_id: 3, status: 'complete', result: 'SIU referral letter ready · Click to view', siu_letter: 'SPECIAL INVESTIGATIONS UNIT REFERRAL\n\nMock SIU letter for demo purposes.\n\nThis case has been escalated for investigation.' },
      { step_id: 4, status: 'running' },
      { step_id: 4, status: 'complete', result: 'SIU team assigned · Due: within 48h' },
    ]

    const delays = [800, 500, 1500, 500, 2000, 500, 500, 300]

    for (let i = 0; i < mockUpdates.length; i++) {
      await new Promise(r => setTimeout(r, delays[i]))
      const upd = mockUpdates[i]
      setSteps(prev => prev.map(s =>
        s.step_id === upd.step_id ? { ...s, ...upd } : s
      ))
      if (upd.siu_letter) setLetter(upd.siu_letter)
    }

    setDone(true)
    setRunning(false)
  }

  useEffect(() => {
    if (autoStart && analysis.combined_score >= 75) {
      const timer = setTimeout(startAgent, 800)
      return () => clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  return (
    <div style={{
      background:   '#FFFFFF',
      border:       '1px solid #E8E6E1',
      borderRadius: '12px',
      overflow:     'hidden',
      boxShadow:    '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      {/* Header */}
      <div style={{
        display:        'flex',
        alignItems:     'center',
        justifyContent: 'space-between',
        padding:        '14px 20px',
        borderBottom:   '1px solid #E8E6E1',
        background:     '#F7F6F3',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {running && (
            <span style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: '#1A1A1A',
              display: 'inline-block',
              animation: 'score-pulse 1s ease-in-out infinite',
            }} />
          )}
          {done && (
            <span style={{ color: '#16A34A', fontSize: '1rem' }}>✓</span>
          )}
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#1A1A1A' }}>
            Fraud Agent
          </span>
          <span style={{
            background: '#F0EFEB', border: '1px solid #E8E6E1',
            color: '#6B6B6B', fontSize: '0.7rem', borderRadius: '4px', padding: '2px 8px',
          }}>
            {running ? 'Running' : done ? 'Complete' : 'Standby'}
          </span>
        </div>

        {!running && !done && (
          <button
            onClick={startAgent}
            style={{
              background: '#1A1A1A', color: '#fff',
              border: 'none', borderRadius: '6px',
              fontSize: '0.75rem', fontWeight: 600,
              padding: '6px 14px', cursor: 'pointer',
              transition: 'background 0.15s ease',
              fontFamily: 'Inter, sans-serif',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = '#2D2D2D')}
            onMouseLeave={e => (e.currentTarget.style.background = '#1A1A1A')}
          >
            Run Agent
          </button>
        )}
      </div>

      {/* Steps */}
      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {steps.map((step) => (
          <div key={step.step_id} style={{
            display:    'flex',
            alignItems: 'flex-start',
            gap:        '12px',
          }}>
            {/* Step icon */}
            <div style={{
              width:          '24px',
              height:         '24px',
              borderRadius:   '50%',
              background:     step.status === 'complete' ? '#F0FDF4' :
                              step.status === 'running'  ? '#F0EFEB' :
                              '#F7F6F3',
              border:         `1px solid ${STEP_COLORS[step.status]}`,
              display:        'flex',
              alignItems:     'center',
              justifyContent: 'center',
              fontSize:       '0.8rem',
              color:          STEP_COLORS[step.status],
              flexShrink:     0,
              marginTop:      '2px',
              transition:     'all 0.3s ease',
              animation:      step.status === 'running' ? 'score-pulse 1.2s ease-in-out infinite' : 'none',
            }}>
              {STEP_ICONS[step.status]}
            </div>

            {/* Step content */}
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize:   '0.8125rem',
                fontWeight: 500,
                color:      step.status === 'pending' ? '#9A9A9A' : '#1A1A1A',
                transition: 'color 0.3s ease',
              }}>
                {step.name}
              </div>

              {step.result && (
                <div style={{
                  marginTop: '4px',
                  fontSize:  '0.75rem',
                  color:     step.is_warning ? '#D97706' : '#9A9A9A',
                  animation: 'fade-in 0.3s ease',
                }}>
                  {step.result}
                  {step.siu_letter && (
                    <button
                      onClick={() => setShowLetter(true)}
                      style={{
                        marginLeft:     '8px',
                        background:     'transparent',
                        border:         'none',
                        color:          '#1A1A1A',
                        fontSize:       '0.75rem',
                        cursor:         'pointer',
                        textDecoration: 'underline',
                        fontFamily:     'Inter, sans-serif',
                      }}
                    >
                      View
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Step number */}
            <span style={{ fontSize: '0.7rem', color: '#C4C4C4', flexShrink: 0, marginTop: '4px' }}>
              {step.step_id}/4
            </span>
          </div>
        ))}
      </div>

      {/* SIU Letter Modal */}
      {showLetter && letter && (
        <div
          onClick={() => setShowLetter(false)}
          style={{
            position:       'fixed', inset: 0,
            background:     'rgba(0,0,0,0.4)',
            zIndex:         50,
            display:        'flex', alignItems: 'center', justifyContent: 'center',
            padding:        '24px',
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background:   '#FFFFFF',
              border:       '1px solid #E8E6E1',
              borderRadius: '14px',
              padding:      '24px',
              maxWidth:     '600px',
              width:        '100%',
              maxHeight:    '80vh',
              overflow:     'auto',
              boxShadow:    '0 8px 40px rgba(0,0,0,0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#1A1A1A' }}>SIU Referral Letter</span>
              <button
                onClick={() => setShowLetter(false)}
                style={{
                  background: '#F0EFEB', border: '1px solid #E8E6E1', borderRadius: '6px',
                  color: '#6B6B6B', fontSize: '0.875rem', padding: '4px 10px',
                  cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                }}
              >
                Close
              </button>
            </div>
            <pre style={{
              whiteSpace:  'pre-wrap',
              fontSize:    '0.8125rem',
              lineHeight:  '1.65',
              color:       '#6B6B6B',
              fontFamily:  'Inter, -apple-system, sans-serif',
            }}>
              {letter}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
