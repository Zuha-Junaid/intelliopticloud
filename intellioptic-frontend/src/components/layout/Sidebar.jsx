import { NavLink } from 'react-router-dom'
import { Cloud, Activity } from 'lucide-react'
import { navItems } from '../../data/navigation'

export default function Sidebar() {
  return (
    <aside className="glass-sidebar hidden lg:flex flex-col w-60 shrink-0 h-screen sticky top-0 p-4">
      {/* Brand */}
      <div className="flex items-center gap-3 px-2 py-3 mb-6">
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
          <p style={{ fontSize: 13, fontWeight: 600, color: '#e8eaee', lineHeight: 1.3 }}>
            IntelliOptiCloud
          </p>
          <p style={{ fontSize: 11, color: '#4a505c' }}>Free Tier v1.7</p>
        </div>
      </div>

      {/* Section label */}
      <p style={{ fontSize: 10, fontWeight: 600, color: '#4a505c', letterSpacing: '0.08em', paddingLeft: 12, marginBottom: 6 }}>
        MAIN MENU
      </p>

      {/* Nav links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}
          >
            <item.icon size={16} strokeWidth={2} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Status chip at bottom */}
      <div
        style={{
          background: 'rgba(61,220,151,0.07)',
          border: '1px solid rgba(61,220,151,0.15)',
          borderRadius: 12,
          padding: '10px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginTop: 8
        }}
      >
        <Activity size={14} color="#3ddc97" />
        <div>
          <p style={{ fontSize: 12, color: '#3ddc97', fontWeight: 600 }}>Engine Active</p>
          <p style={{ fontSize: 10, color: '#4a505c', marginTop: 1 }}>Zero downtime · Autonomous</p>
        </div>
      </div>
    </aside>
  )
}