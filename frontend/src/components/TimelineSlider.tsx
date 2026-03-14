/**
 * TimelineSlider — filters the fraud graph by date.
 * Drag the slider → edges with timestamps after this date disappear.
 * Shows how the fraud ring built up over time.
 */

import { useState, useMemo } from 'react'
import type { GraphEdge } from '../types'
import { formatDate } from '../lib/utils'

interface Props {
  edges: GraphEdge[]
  onChange: (filterDate: string) => void
}

export function TimelineSlider({ edges, onChange }: Props) {
  // Find date range from edges
  const { minDate, maxDate, dates } = useMemo(() => {
    const sortedDates = [...new Set(edges.map(e => e.timestamp))].sort()
    if (sortedDates.length === 0) return { minDate: '', maxDate: '', dates: [] }
    return {
      minDate: sortedDates[0],
      maxDate: sortedDates[sortedDates.length - 1],
      dates:   sortedDates,
    }
  }, [edges])

  const [currentIdx, setCurrentIdx] = useState(dates.length - 1)
  const currentDate = dates[currentIdx] || maxDate

  if (dates.length <= 1) return null

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value)
    setCurrentIdx(idx)
    onChange(dates[idx])
  }

  const resetToAll = () => {
    const last = dates.length - 1
    setCurrentIdx(last)
    onChange(dates[last])
  }

  return (
    <div style={{
      background:   '#161325',
      border:       '1px solid #2A2640',
      borderRadius: '10px',
      padding:      '14px 16px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div>
          <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#fff' }}>Timeline</span>
          <span style={{ fontSize: '0.75rem', color: '#6B6680', marginLeft: '8px' }}>
            Showing edges through {formatDate(currentDate)}
          </span>
        </div>
        {currentIdx < dates.length - 1 && (
          <button
            onClick={resetToAll}
            style={{
              background: 'transparent',
              border: '1px solid #2A2640',
              borderRadius: '6px',
              color: '#A09BB8',
              fontSize: '0.75rem',
              padding: '3px 8px',
              cursor: 'pointer',
            }}
          >
            Show all
          </button>
        )}
      </div>

      {/* Slider */}
      <input
        type="range"
        min={0}
        max={dates.length - 1}
        value={currentIdx}
        onChange={handleChange}
        style={{
          width:   '100%',
          cursor:  'pointer',
          accentColor: '#6B21F5',
        }}
      />

      {/* Date labels */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
        <span style={{ fontSize: '0.7rem', color: '#6B6680' }}>{formatDate(minDate)}</span>
        <span style={{ fontSize: '0.7rem', color: '#6B6680' }}>{formatDate(maxDate)}</span>
      </div>

      {/* Edge count indicator */}
      <div style={{
        marginTop: '8px',
        fontSize: '0.75rem',
        color: '#6B6680',
        textAlign: 'center',
      }}>
        {edges.filter(e => e.timestamp <= currentDate).length} of {edges.length} edges visible
      </div>
    </div>
  )
}
