import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../lib/api'

export function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totp, setTotp]         = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [showTotp, setShowTotp] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.login(username, password, totp || undefined)
      localStorage.setItem('cs_token', res.access_token)
      localStorage.setItem('cs_user', JSON.stringify({ username: res.username, role: res.role }))
      navigate('/dashboard')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Login failed'
      if (msg.includes('TOTP') || msg.includes('2FA')) {
        setShowTotp(true)
        setError('Please enter your 6-digit TOTP code')
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F5F4F0', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
      <div style={{ width: '100%', maxWidth: '380px' }}>

        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '36px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '44px', height: '44px', background: '#1A1A1A', borderRadius: '10px', fontSize: '0.7rem', fontWeight: 700, color: '#fff', marginBottom: '14px' }}>
            CS
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1A1A1A', letterSpacing: '-0.02em' }}>ClaimShield</h1>
          <p style={{ color: '#9A9A9A', fontSize: '0.8125rem', marginTop: '4px' }}>AI Fraud Detection · IBM watsonx.ai</p>
        </div>

        {/* Card */}
        <div style={{ background: '#FFFFFF', border: '1px solid #E8E6E1', borderRadius: '12px', padding: '28px', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
          <h2 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#1A1A1A', marginBottom: '20px' }}>Sign in to your account</h2>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: '#9A9A9A', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="admin" autoComplete="username" required className="input" />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: '#9A9A9A', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password" required className="input" />
            </div>
            {showTotp && (
              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: '#9A9A9A', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Authenticator Code</label>
                <input type="text" value={totp} onChange={e => setTotp(e.target.value)} placeholder="123456" maxLength={6} pattern="[0-9]{6}" className="input" style={{ letterSpacing: '0.2em', textAlign: 'center', fontFamily: 'monospace' }} />
              </div>
            )}
            {error && (
              <div style={{ background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: '8px', padding: '10px 14px', color: '#DC2626', fontSize: '0.8125rem' }}>{error}</div>
            )}
            <button type="submit" disabled={loading} className="btn-primary" style={{ width: '100%', marginTop: '4px' }}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div style={{ marginTop: '18px', padding: '12px', background: '#F7F6F3', borderRadius: '8px', fontSize: '0.75rem', color: '#9A9A9A', border: '1px solid #F0EFEB' }}>
            <div style={{ fontWeight: 600, color: '#6B6B6B', marginBottom: '4px' }}>Demo credentials</div>
            <div>admin / admin123</div>
            <div>adjuster1 / pass123</div>
            <div>investigator1 / pass123</div>
          </div>
        </div>
      </div>
    </div>
  )
}
