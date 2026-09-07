import { useState, useEffect } from 'react'
import { TrendingDown, TrendingUp, Zap, Server, RefreshCw } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { dashboardAPI } from '../lib/api'

const fmt = (n) => `PKR ${Number(n).toLocaleString()}`

function KPICard({ label, value, sub, icon: Icon, cyan }) {
  return (
    <div className="glass-card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-titanium-500 uppercase tracking-wider">{label}</p>
        <Icon size={16} className="text-titanium-700" />
      </div>
      <p className={`text-2xl font-bold ${cyan ? 'text-cyan-glow' : 'text-titanium-100'}`}>{value}</p>
      {sub && <p className="text-[11px] text-titanium-500">{sub}</p>}
    </div>
  )
}

function Skeleton() {
  return <div className="glass-card p-4 h-28 animate-pulse bg-white/5" />
}

const Tip = ({ active, payload, label }) => active && payload?.length ? (
  <div className="glass-strong rounded-xl p-3 text-xs">
    <p className="text-titanium-300 mb-1">{label}</p>
    {payload.map(p => <p key={p.name} style={{ color: p.color }}>{p.name}: {fmt(p.value)}</p>)}
  </div>
) : null

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try { setData(await dashboardAPI.getSummary()) }
    catch { setError('Could not load dashboard. Is the backend running?') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const cs = data?.costSummary
  const trend = data?.savingsTrend || []
  const health = data?.systemHealth

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Dashboard</h1>
          <p className="text-xs text-titanium-500 mt-0.5">Real-time AWS cost optimization — autonomous engine running</p>
        </div>
        <button onClick={load} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {loading ? Array(4).fill(0).map((_, i) => <Skeleton key={i} />) : <>
          <KPICard label="Monthly Bill" value={fmt(cs?.currentMonthly || 0)} sub={`Was ${fmt(cs?.previousMonthly || 0)}`} icon={TrendingDown} cyan />
          <KPICard label="Total Saved" value={fmt(cs?.savedAmount || 0)} sub="This month" icon={TrendingUp} />
          <KPICard label="Savings Rate" value={`${cs?.savingsPercent || 0}%`} sub="vs baseline" icon={Zap} />
          <KPICard label="Functions" value={health?.functionsMonitored || 0} sub={`Optimized ${health?.lastOptimized}`} icon={Server} />
        </>}
      </div>

      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <h2 className="text-sm font-semibold text-titanium-100">Cost Savings Trend</h2>
            <p className="text-xs text-titanium-500">Monthly PKR — before vs. after optimization</p>
          </div>
          <span className="cyan-badge">↓ {cs?.savingsPercent || 0}% reduction</span>
        </div>
        {loading
          ? <div className="h-52 bg-white/5 rounded-xl animate-pulse" />
          : <ResponsiveContainer width="100%" height={200} minWidth={0}>
              <AreaChart data={trend} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="gBefore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f0594e" stopOpacity={0.15} /><stop offset="95%" stopColor="#f0594e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gAfter" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4ee3f0" stopOpacity={0.15} /><stop offset="95%" stopColor="#4ee3f0" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="month" tick={{ fill: '#7d8492', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#7d8492', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `${v/1000}k`} width={34} />
                <Tooltip content={<Tip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#7d8492' }} />
                <Area type="monotone" dataKey="before" name="Before" stroke="#f0594e" strokeWidth={2} fill="url(#gBefore)" />
                <Area type="monotone" dataKey="after" name="After" stroke="#4ee3f0" strokeWidth={2} fill="url(#gAfter)" />
              </AreaChart>
            </ResponsiveContainer>
        }
      </div>

      {!loading && health && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[['Uptime', health.uptime], ['Actions Today', health.actionsToday],
            ['Last Optimized', health.lastOptimized], ['Functions Active', health.functionsMonitored]
          ].map(([label, value]) => (
            <div key={label} className="glass-card p-3 text-center">
              <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">{label}</p>
              <p className="text-sm font-semibold text-titanium-100">{value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}