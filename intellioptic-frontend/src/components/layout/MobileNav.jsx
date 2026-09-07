import { useState } from 'react'
import { createPortal } from 'react-dom'
import { NavLink } from 'react-router-dom'
import { Menu, X, Cloud, Activity } from 'lucide-react'
import { navItems } from '../../data/navigation'
 
export default function MobileNav() {
  const [open, setOpen] = useState(false)
 
  const drawer = (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 99999,
      }}
    >
      {/* Dark overlay covering full viewport */}
      <div
        onClick={() => setOpen(false)}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          background: 'rgba(0,0,0,0.75)',
        }}
      />
 
      {/* Drawer panel */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          height: '100vh',
          width: '280px',
          maxWidth: '85vw',
          background: '#0a0d12',
          borderRight: '1px solid rgba(255,255,255,0.08)',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '8px 0 40px rgba(0,0,0,0.5)',
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 8px', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(78,227,240,0.25), rgba(61,82,144,0.35))',
                border: '1px solid rgba(78,227,240,0.25)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}
            >
              <Cloud size={18} color="#4ee3f0" strokeWidth={2} />
            </div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: '#e8eaee', lineHeight: 1.3, margin: 0 }}>
                IntelliOptiCloud
              </p>
              <p style={{ fontSize: 11, color: '#4a505c', margin: 0 }}>Free Tier v1.7</p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            aria-label="Close navigation menu"
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 4 }}
          >
            <X size={20} color="#7d8492" />
          </button>
        </div>
 
        <p style={{ fontSize: 10, fontWeight: 600, color: '#4a505c', letterSpacing: '0.08em', paddingLeft: 12, marginBottom: 8 }}>
          MAIN MENU
        </p>
 
        {/* Nav links */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}
            >
              <item.icon size={16} strokeWidth={2} />
              {item.label}
            </NavLink>
          ))}
        </nav>
 
        {/* Status footer */}
        <div
          style={{
            background: 'rgba(61,220,151,0.1)',
            border: '1px solid rgba(61,220,151,0.2)',
            borderRadius: 12,
            padding: '10px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 8,
            flexShrink: 0,
          }}
        >
          <Activity size={14} color="#3ddc97" />
          <div>
            <p style={{ fontSize: 12, color: '#3ddc97', fontWeight: 600, margin: 0 }}>Engine Active</p>
            <p style={{ fontSize: 10, color: '#4a505c', marginTop: 1, marginBottom: 0 }}>Zero downtime · Autonomous</p>
          </div>
        </div>
      </div>
    </div>
  )
 
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="lg:hidden flex items-center justify-center w-9 h-9 rounded-lg hover:bg-white/5 shrink-0"
        aria-label="Open navigation menu"
      >
        <Menu size={20} color="#e8eaee" />
      </button>
 
      {/* Render the drawer directly into document.body, bypassing any parent layout context */}
      {open && createPortal(drawer, document.body)}
    </>
  )
}