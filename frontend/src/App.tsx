import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LoginPage }       from './pages/LoginPage'
import { DashboardPage }   from './pages/DashboardPage'
import { ReportPage }      from './pages/ReportPage'
import { SubmitClaimPage } from './pages/SubmitClaimPage'
import { ClaimsPage }      from './pages/ClaimsPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('cs_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const user     = JSON.parse(localStorage.getItem('cs_user') || '{}')

  const logout = () => {
    localStorage.removeItem('cs_token')
    localStorage.removeItem('cs_user')
    navigate('/login')
  }

  const navItems = [
    { path: '/dashboard',  label: 'Dashboard' },
    { path: '/claims',     label: 'Claims'    },
    { path: '/claims/new', label: 'New Claim' },
  ]

  const isActive = (path: string) =>
    path === '/dashboard'
      ? location.pathname === '/dashboard'
      : location.pathname.startsWith(path)

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#F5F4F0' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width:         '200px',
        flexShrink:    0,
        background:    '#FFFFFF',
        borderRight:   '1px solid #E8E6E1',
        display:       'flex',
        flexDirection: 'column',
        padding:       '20px 12px',
        position:      'sticky',
        top:           0,
        height:        '100vh',
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 8px', marginBottom: '28px' }}>
          <div style={{
            width: '26px', height: '26px',
            background: '#1A1A1A',
            borderRadius: '6px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.65rem', fontWeight: 700, color: '#fff', flexShrink: 0,
          }}>
            CS
          </div>
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#1A1A1A', lineHeight: 1.1 }}>ClaimShield</div>
            <div style={{ fontSize: '0.6rem', color: '#9A9A9A', marginTop: '1px' }}>watsonx.ai</div>
          </div>
        </div>

        {/* Section label */}
        <div style={{ fontSize: '0.6rem', fontWeight: 600, color: '#C4C4C4', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '0 10px', marginBottom: '6px' }}>
          Navigation
        </div>

        {/* Nav */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
          {navItems.map(item => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`sidebar-item${isActive(item.path) ? ' active' : ''}`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* User */}
        <div style={{ borderTop: '1px solid #E8E6E1', paddingTop: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', marginBottom: '4px' }}>
            <div style={{
              width: '24px', height: '24px', borderRadius: '50%',
              background: '#F0EFEB', border: '1px solid #E8E6E1',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.65rem', color: '#6B6B6B', fontWeight: 700, flexShrink: 0,
            }}>
              {(user.username || 'U')[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#1A1A1A', lineHeight: 1 }}>
                {user.username}
              </div>
              <div style={{ fontSize: '0.65rem', color: '#9A9A9A', marginTop: '2px', textTransform: 'capitalize' }}>
                {user.role}
              </div>
            </div>
          </div>
          <button onClick={logout} className="sidebar-item" style={{ color: '#9A9A9A', fontSize: '0.75rem' }}>
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ flex: 1, padding: '32px 36px', overflowY: 'auto', maxWidth: 'calc(100vw - 200px)' }}>
        {children}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#FFFFFF',
            color: '#1A1A1A',
            border: '1px solid #E8E6E1',
            borderRadius: '8px',
            fontSize: '0.875rem',
            boxShadow: '0 4px 12px rgba(0,0,0,0.10)',
          },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<RequireAuth><Layout><DashboardPage /></Layout></RequireAuth>} />
        <Route path="/claims" element={<RequireAuth><Layout><ClaimsPage /></Layout></RequireAuth>} />
        <Route path="/claims/new" element={<RequireAuth><Layout><SubmitClaimPage /></Layout></RequireAuth>} />
        <Route path="/report/:claimToken" element={<RequireAuth><Layout><ReportPage /></Layout></RequireAuth>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
