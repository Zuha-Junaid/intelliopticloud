import { useState, useEffect } from 'react'
import { CheckCheck, Zap, AlertTriangle, Info, Lightbulb, BellOff, RefreshCw } from 'lucide-react'
import { notificationsAPI } from '../lib/api'
import { timeAgo } from '../lib/format'

const ICONS = {
  action: { icon: Zap, color: '#3ddc97', bg: 'rgba(61,220,151,0.12)' },
  recommendation: { icon: Lightbulb, color: '#4ee3f0', bg: 'rgba(78,227,240,0.12)' },
  alert: { icon: AlertTriangle, color: '#f0b94e', bg: 'rgba(240,185,78,0.12)' },
  system: { icon: Info, color: '#7d8492', bg: 'rgba(125,132,146,0.12)' },
}
const TABS = ['All', 'Unread', 'Action', 'Recommendation', 'Alert', 'System']

export default function Notifications() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('All')
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try { const r = await notificationsAPI.getAll(); setItems(r.notifications || []) }
    catch { setItems([]); setError('Could not load notifications. Is the backend running?') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const markAll = async () => {
    await notificationsAPI.markAllRead()
    setItems(p => p.map(n => ({ ...n, read: true })))
  }

  const markOne = async (id) => {
    await notificationsAPI.markRead(id)
    setItems(p => p.map(n => n.id === id ? { ...n, read: true } : n))
  }

  const filtered = items.filter(n => {
    if (tab === 'All') return true
    if (tab === 'Unread') return !n.read
    return n.type === tab.toLowerCase()
  })

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Notifications</h1>
          <p className="text-xs text-titanium-500 mt-0.5">
            {items.filter(n => !n.read).length} unread. Created by monitoring cycles and applied changes; choose what you receive in Settings.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="glass-card px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100" aria-label="Refresh">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={markAll} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
            <CheckCheck size={14} /> Mark all read
          </button>
        </div>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}

      <div className="flex gap-1.5 flex-wrap">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${tab === t ? 'border-cyan-glow/30 bg-cyan-glow/10 text-cyan-glow' : 'border-white/10 text-titanium-500 hover:text-titanium-100'}`}>
            {t}
          </button>
        ))}
      </div>

      <div className="glass-card divide-y divide-white/5 overflow-hidden">
        {loading ? Array(4).fill(0).map((_, i) => (
          <div key={i} className="flex gap-3 px-5 py-4 animate-pulse">
            <div className="w-8 h-8 rounded-lg bg-white/10 shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-3 bg-white/10 rounded w-48" />
              <div className="h-3 bg-white/10 rounded w-64" />
            </div>
          </div>
        )) : filtered.length === 0 ? (
          <div className="py-16 flex flex-col items-center gap-2 px-4 text-center">
            <BellOff size={28} className="text-titanium-700" />
            <p className="text-titanium-500 text-sm">No notifications yet.</p>
            <p className="text-titanium-700 text-xs">They appear after a monitoring cycle finds a recommendation, a usage increase or a change is applied.</p>
          </div>
        ) : filtered.map(n => {
          const meta = ICONS[n.type] || ICONS.system
          const Icon = meta.icon
          return (
            <div key={n.id} onClick={() => !n.read && markOne(n.id)}
              className={`flex gap-3 px-4 py-4 cursor-pointer hover:bg-white/4 transition-colors ${!n.read ? 'bg-white/3' : ''}`}>
              <div style={{ width: 32, height: 32, borderRadius: 9, flexShrink: 0, background: meta.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={15} color={meta.color} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-medium text-titanium-100">{n.title}</p>
                  {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-cyan-glow shrink-0" />}
                </div>
                <p className="text-[11px] text-titanium-500 mt-1">{n.desc}</p>
                <p className="text-[10px] text-titanium-700 mt-1">{timeAgo(n.createdAt)}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
