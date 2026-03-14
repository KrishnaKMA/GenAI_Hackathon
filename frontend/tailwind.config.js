/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand:          '#6B21F5',
        'brand-light':  '#7C3AED',
        'brand-glow':   '#8B5CF6',
        'brand-muted':  '#4C1D95',
        'brand-subtle': '#2D1B69',
        surface:            '#161325',
        'surface-secondary':'#12101F',
        'surface-tertiary': '#1A1728',
        'surface-card':     '#161325',
        'surface-overlay':  '#1E1B2E',
        'border-default':   '#2A2640',
        'border-subtle':    '#1E1B30',
        'border-active':    '#6B21F5',
        'text-primary':     '#FFFFFF',
        'text-secondary':   '#A09BB8',
        'text-muted':       '#6B6680',
        'text-disabled':    '#3D3A52',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        card:              '0 4px 24px rgba(0,0,0,0.4)',
        'purple-glow':     '0 0 24px rgba(107,33,245,0.35)',
        'purple-glow-lg':  '0 0 40px rgba(107,33,245,0.5)',
      },
      animation: {
        'node-pulse': 'node-pulse 2s ease-in-out infinite alternate',
        'fade-in':    'fade-in 0.3s ease',
        'shimmer':    'shimmer 1.5s ease infinite',
      },
      keyframes: {
        'node-pulse': {
          '0%':   { boxShadow: '0 0 8px rgba(239,68,68,0.4)' },
          '100%': { boxShadow: '0 0 24px rgba(239,68,68,0.9)' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '14px',
        xl: '20px',
        card: '12px',
      },
    },
  },
  plugins: [],
}
