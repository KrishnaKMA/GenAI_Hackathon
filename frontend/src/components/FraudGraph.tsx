/**
 * FraudGraph — Cytoscape.js entity relationship graph.
 * Shows claimants, providers, repair shops as nodes with fraud-colored edges.
 *
 * Features:
 * - CRITICAL nodes pulse red
 * - Click a node → shows details tooltip
 * - Timeline slider filters edges by date
 * - Layout selector: cose / circle / breadthfirst
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape from 'cytoscape'
import type { Core, NodeSingular } from 'cytoscape'
import type { GraphNode, GraphEdge, GNNEvidence } from '../types'
import { cytoscapeStyles, graphLayouts } from '../lib/cytoscapeConfig'
import { truncateToken, formatDate } from '../lib/utils'

interface Props {
  nodes: GraphNode[]
  edges: GraphEdge[]
  evidence?: GNNEvidence[]
  highlightedEdges?: string[]   // "source→target" keys to highlight
  filterDate?: string           // ISO date — hides edges after this date
}

interface NodeTooltip {
  id: string
  type: string
  fraud_score: number
  claim_count: number
  is_flagged: boolean
  x: number
  y: number
}

const LAYOUT_OPTIONS = ['cose', 'circle', 'breadthfirst', 'grid'] as const
type LayoutName = typeof LAYOUT_OPTIONS[number]

export function FraudGraph({ nodes, edges, evidence = [], highlightedEdges = [], filterDate }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef        = useRef<Core | null>(null)
  const [tooltip, setTooltip]   = useState<NodeTooltip | null>(null)
  const [layout, setLayout]     = useState<LayoutName>('cose')
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)

  // Build highlighted edge set for fast lookup
  const highlightedSet = new Set(highlightedEdges)

  // Evidence edge set
  const evidenceEdges = new Set(
    evidence.map(e => `${e.source_token}→${e.target_token}`)
  )

  const initGraph = useCallback(() => {
    if (!containerRef.current || nodes.length === 0) return

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy()
      cyRef.current = null
    }

    // Filter edges by date if filterDate set
    const visibleEdges = filterDate
      ? edges.filter(e => e.timestamp <= filterDate)
      : edges

    // Build Cytoscape elements
    const cyNodes = nodes.map(n => ({
      data: {
        id:          n.id,
        label:       truncateToken(n.id, 10),
        node_type:   n.type,
        fraud_score: n.fraud_score,
        claim_count: n.claim_count,
        is_flagged:  n.is_flagged,
      },
    }))

    const cyEdges = visibleEdges.map((e, i) => {
      const key = `${e.source}→${e.target}`
      const isEvidence    = evidenceEdges.has(key)
      const isHighlighted = highlightedSet.has(key)
      return {
        data: {
          id:          `e_${i}`,
          source:      e.source,
          target:      e.target,
          edge_type:   e.edge_type,
          weight:      e.weight,
          timestamp:   e.timestamp,
        },
        classes: [
          isEvidence    ? 'highlighted' : '',
          isHighlighted ? 'highlighted' : '',
        ].filter(Boolean).join(' '),
      }
    })

    setNodeCount(cyNodes.length)
    setEdgeCount(cyEdges.length)

    const cy = cytoscape({
      container:  containerRef.current,
      elements:   [...cyNodes, ...cyEdges],
      style:      cytoscapeStyles,
      layout:     graphLayouts[layout] as any,
      userZoomingEnabled:    true,
      userPanningEnabled:    true,
      boxSelectionEnabled:   false,
      autoungrabify:         false,
      minZoom: 0.3,
      maxZoom: 3,
    })

    cyRef.current = cy

    // Node click → show tooltip
    cy.on('tap', 'node', (evt) => {
      const node = evt.target as NodeSingular
      const renderedPos = node.renderedPosition()
      const data = node.data()

      setTooltip({
        id:          data.id,
        type:        data.node_type,
        fraud_score: data.fraud_score,
        claim_count: data.claim_count,
        is_flagged:  data.is_flagged,
        x:           renderedPos.x,
        y:           renderedPos.y,
      })
    })

    // Click on background → close tooltip
    cy.on('tap', (evt) => {
      if (evt.target === cy) setTooltip(null)
    })

    // Fit graph on load
    cy.fit(undefined, 30)

  }, [nodes, edges, evidence, filterDate, layout])

  useEffect(() => {
    initGraph()
    return () => {
      if (cyRef.current) cyRef.current.destroy()
    }
  }, [initGraph])

  const relayout = (name: LayoutName) => {
    setLayout(name)
    setTooltip(null)
    if (cyRef.current) {
      cyRef.current.layout(graphLayouts[name] as any).run()
    }
  }

  const resetView = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 30)
      setTooltip(null)
    }
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', background: '#0D0B1A', borderRadius: '12px', overflow: 'hidden' }}>

      {/* Controls */}
      <div style={{
        position:   'absolute', top: 12, left: 12, zIndex: 10,
        display:    'flex', gap: '8px', flexWrap: 'wrap',
      }}>
        {LAYOUT_OPTIONS.map(name => (
          <button
            key={name}
            onClick={() => relayout(name)}
            style={{
              background:   layout === name ? '#6B21F5' : 'rgba(22,19,37,0.9)',
              border:       `1px solid ${layout === name ? '#6B21F5' : '#2A2640'}`,
              borderRadius: '6px',
              color:        layout === name ? '#fff' : '#A09BB8',
              fontSize:     '0.75rem',
              fontWeight:   500,
              padding:      '4px 10px',
              cursor:       'pointer',
              backdropFilter: 'blur(8px)',
              transition:   'all 0.15s ease',
            }}
          >
            {name}
          </button>
        ))}
        <button
          onClick={resetView}
          style={{
            background:   'rgba(22,19,37,0.9)',
            border:       '1px solid #2A2640',
            borderRadius: '6px',
            color:        '#A09BB8',
            fontSize:     '0.75rem',
            fontWeight:   500,
            padding:      '4px 10px',
            cursor:       'pointer',
            backdropFilter: 'blur(8px)',
          }}
        >
          ⊹ fit
        </button>
      </div>

      {/* Stats */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 10,
        background: 'rgba(22,19,37,0.9)',
        border: '1px solid #2A2640',
        borderRadius: '8px',
        padding: '6px 12px',
        backdropFilter: 'blur(8px)',
        fontSize: '0.75rem',
        color: '#6B6680',
      }}>
        {nodeCount} nodes · {edgeCount} edges
      </div>

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12, zIndex: 10,
        background: 'rgba(22,19,37,0.9)',
        border: '1px solid #2A2640',
        borderRadius: '8px',
        padding: '8px 12px',
        backdropFilter: 'blur(8px)',
        display: 'flex', flexDirection: 'column', gap: '4px',
      }}>
        {[
          { color: '#3B82F6', label: 'Claimant' },
          { color: '#6B7280', label: 'Provider' },
          { color: '#F59E0B', label: 'Repair Shop' },
          { color: '#EF4444', label: 'Flagged' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.color, flexShrink: 0 }} />
            <span style={{ fontSize: '0.7rem', color: '#A09BB8' }}>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Cytoscape container */}
      <div ref={containerRef} id="cy" style={{ width: '100%', height: '100%' }} />

      {/* Node tooltip */}
      {tooltip && (
        <div style={{
          position:     'absolute',
          left:         tooltip.x + 16,
          top:          tooltip.y - 20,
          zIndex:       20,
          background:   '#161325',
          border:       '1px solid #2A2640',
          borderRadius: '10px',
          padding:      '12px 16px',
          minWidth:     '180px',
          boxShadow:    '0 4px 24px rgba(0,0,0,0.5)',
          pointerEvents:'none',
          animation:    'fade-in 0.2s ease',
        }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#fff', marginBottom: '8px' }}>
            {tooltip.id}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {[
              { label: 'Type',       value: tooltip.type },
              { label: 'Claims',     value: tooltip.claim_count },
              { label: 'Fraud Score',value: `${tooltip.fraud_score}/100` },
              { label: 'Flagged',    value: tooltip.is_flagged ? '⚠️ Yes' : '✓ No' },
            ].map(row => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: '#6B6680' }}>{row.label}</span>
                <span style={{
                  fontSize:  '0.75rem',
                  fontWeight: 500,
                  color: row.label === 'Flagged' && tooltip.is_flagged ? '#EF4444' : '#A09BB8',
                }}>
                  {String(row.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {nodes.length === 0 && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#6B6680', fontSize: '0.875rem',
        }}>
          No graph data available
        </div>
      )}
    </div>
  )
}
