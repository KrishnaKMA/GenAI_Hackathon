/**
 * FraudScoreBadge — shows the combined fraud score + risk level.
 * CRITICAL badge pulses with animation.
 */

import type { RiskLevel } from '../types'
import { riskColors } from '../lib/utils'

interface Props {
  score: number
  riskLevel: RiskLevel
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

export function FraudScoreBadge({ score, riskLevel, size = 'md', showLabel = true }: Props) {
  const colors = riskColors[riskLevel]
  const isCritical = riskLevel === 'CRITICAL'

  const sizeStyles = {
    sm:  { fontSize: '0.75rem', padding: '3px 10px', scoreSize: '1rem' },
    md:  { fontSize: '0.8125rem', padding: '5px 14px', scoreSize: '1.25rem' },
    lg:  { fontSize: '0.9375rem', padding: '8px 20px', scoreSize: '1.75rem' },
  }[size]

  return (
    <div
      className={isCritical ? 'score-critical-pulse' : ''}
      style={{
        display:         'inline-flex',
        alignItems:      'center',
        gap:             '8px',
        background:      colors.bg,
        border:          colors.border,
        borderRadius:    '9999px',
        padding:         sizeStyles.padding,
        userSelect:      'none',
      }}
    >
      {/* Score number */}
      <span style={{
        color:      colors.text,
        fontSize:   sizeStyles.scoreSize,
        fontWeight: 700,
        lineHeight: 1,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {Math.round(score)}
      </span>

      {showLabel && (
        <>
          <span style={{ color: colors.text, opacity: 0.5, fontSize: sizeStyles.fontSize }}>/100</span>
          <span style={{
            color:        colors.text,
            fontSize:     sizeStyles.fontSize,
            fontWeight:   600,
            letterSpacing: '0.05em',
          }}>
            {riskLevel}
          </span>
        </>
      )}

      {/* Pulsing dot for CRITICAL */}
      {isCritical && (
        <span style={{
          width:        '6px',
          height:       '6px',
          borderRadius: '50%',
          background:   colors.text,
          display:      'inline-block',
          flexShrink:   0,
        }} />
      )}
    </div>
  )
}

/** Smaller inline version for table cells */
export function RiskChip({ riskLevel }: { riskLevel: RiskLevel }) {
  const colors = riskColors[riskLevel]
  return (
    <span style={{
      background:    colors.bg,
      border:        colors.border,
      color:         colors.text,
      borderRadius:  '9999px',
      padding:       '2px 10px',
      fontSize:      '0.7rem',
      fontWeight:    600,
      letterSpacing: '0.06em',
      whiteSpace:    'nowrap',
    }}>
      {riskLevel}
    </span>
  )
}
