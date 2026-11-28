import { useState, useEffect } from 'react'
import { TrendingDown, TrendingUp, Zap, Server, RefreshCw } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { dashboardAPI } from '../lib/api'
import { fmtPKR as fmt, timeAgo } from '../lib/format'
import SourceBanner from '../components/SourceBanner'

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
    catch { setError('Could not load the dashboard. Is the backend running?') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const cs = data?.costSummary
  const health = data?.systemHealth
  const history = (data?.costHistory || []).map(h => ({
    time: new Date(h.at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
    cost: h.cost,
  }))

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Dashboard</h1>
          <p className="text-xs text-titanium-500 mt-0.5">Estimated Lambda cost at AWS list prices and savings measured after applied changes</p>
        </div>
        <button onClick={load} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}
      {data && <SourceBanner source={data.source} warning={data.warning} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {loading ? Array(4).fill(0).map((_, i) => <Skeleton key={i} />) : <>
          <KPICard label="Estimated Monthly Cost" value={fmt(cs?.currentMonthly)} sub={cs?.savedAmount > 0 ? `Would be ${fmt(cs?.previousMonthly)} without applied changes` : 'Last 30 days of usage, list price'} icon={TrendingDown} cyan />
          <KPICard label="Verified Savings" value={fmt(cs?.savedAmount)} sub="Per month, measured after applied changes" icon={TrendingUp} />
          <KPICard label="Savings Rate" value={`${cs?.savingsPercent || 0}%`} sub="Of the cost without changes" icon={Zap} />
          <KPICard label="Functions Monitored" value={health?.functionsMonitored || 0} sub={`Last change applied: ${timeAgo(health?.lastOptimized)}`} icon={Server} />
        </>}
      </div>

      <div className="glass-card p-5">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-titanium-100">Recorded Cost History</h2>
          <p className="text-xs text-titanium-500">Estimated monthly cost recorded by each monitoring cycle (last 30 days)</p>
        </div>
        {loading
          ? <div className="h-52 bg-white/5 rounded-xl animate-pulse" />
          : history.length < 2
            ? <div className="h-40 flex items-center justify-center text-center px-4">
                <p className="text-xs text-titanium-500">
                  {data?.source === 'aws'
                    ? 'History builds up as monitoring cycles run. Open Optimization and press Run Cycle Now, or wait for the scheduled job.'
                    : 'History is stored only for a connected AWS account.'}
                </p>
              </div>
            : <ResponsiveContainer width="100%" height={200} minWidth={0}>
                <LineChart data={history} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="time" tick={{ fill: '#7d8492', fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={30} />
                  <YAxis tick={{ fill: '#7d8492', fontSize: 10 }} axisLine={false} tickLine={false} width={40} />
                  <Tooltip content={<Tip />} />
                  <Line type="monotone" dataKey="cost" name="Estimated cost" stroke="#4ee3f0" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
        }
      </div>

      {!loading && health && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[['Server Uptime', `${health.serverUptimeHours} h`], ['Changes Applied Today', health.actionsToday],
            ['Last Change Applied', timeAgo(health.lastOptimized)], ['Last Monitoring Cycle', timeAgo(health.lastCycle)]
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
