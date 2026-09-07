import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, LogOut, ChevronDown } from 'lucide-react'
import MobileNav from './MobileNav'
import { useAuth } from '../../context/AuthContext'
 
export default function Topbar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
 
  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U'
 
  const handleLogout = () => {
    logout()
    navigate('/login')
  }
 
  return (
    <header
      className="glass-topbar sticky top-0 z-20 h-14 flex items-center justify-between px-4 lg:px-6 gap-3"
    >
      {/* Left: hamburger (mobile) + search */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <MobileNav />
 
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 10, padding: '7px 12px',
          }}
          className="w-full max-w-[260px]"
        >
          <Search size={14} color="#4a505c" className="shrink-0" />
          <input
            type="text"
            placeholder="Search..."
            style={{
              background: 'transparent', outline: 'none', border: 'none',
              fontSize: 13, color: '#e8eaee', width: '100%'
            }}
          />
          <kbd className="hidden md:inline" style={{
            fontSize: 10, color: '#4a505c',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 5, padding: '2px 5px'
          }}>⌘K</kbd>
        </div>
      </div>
 
      {/* Right */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }} className="shrink-0 relative">
        {/* Bell */}
        <button
          style={{
            width: 34, height: 34, borderRadius: 8,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', position: 'relative'
          }}
        >
          <Bell size={15} color="#b8bdc7" />
          <span style={{
            position: 'absolute', top: 7, right: 7,
            width: 7, height: 7, borderRadius: '50%',
            background: '#4ee3f0',
            boxShadow: '0 0 6px rgba(78,227,240,0.6)'
          }} />
        </button>
 
        {/* User menu */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', background: 'transparent', border: 'none' }}
          >
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'linear-gradient(135deg, #2c3e6b, #1a1f29)',
              border: '1px solid rgba(255,255,255,0.10)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700, color: '#e8eaee'
            }}>
              {initials}
            </div>
            <div className="hidden sm:block" style={{ textAlign: 'left' }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#e8eaee', lineHeight: 1.3, margin: 0 }}>
                {user?.name || 'User'}
              </p>
              <p style={{ fontSize: 10, color: '#4a505c', margin: 0 }}>{user?.accountType || 'Account'}</p>
            </div>
            <ChevronDown size={14} color="#4a505c" className="hidden sm:block" />
          </button>
 
          {menuOpen && (
            <div
              style={{
                position: 'absolute', right: 0, top: 'calc(100% + 8px)',
                width: 180, background: '#0e1218',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12, padding: 6, zIndex: 50,
              }}
            >
              <div style={{ padding: '8px 10px', borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 4 }}>
                <p style={{ fontSize: 11, color: '#7d8492', margin: 0 }}>{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px', borderRadius: 8, background: 'transparent', border: 'none',
                  fontSize: 12, color: '#f0594e', cursor: 'pointer'
                }}
              >
                <LogOut size={14} /> Log Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}