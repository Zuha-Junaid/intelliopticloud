import { useState, useEffect } from 'react'
import { Download, TrendingDown, FileText, FileSpreadsheet, RefreshCw } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, LineChart, Line } from 'recharts'
import { reportsAPI } from '../lib/api'
import { fmtPKR as fmt, downloadCSV } from '../lib/format'
import SourceBanner from '../components/SourceBanner'

const COLORS = ['#4ee3f0', '#3d5290', '#3ddc97', '#f0b94e', '#f0594e', '#7d8492', '#7ff0fa']
const RANGES = [['7D', 7], ['30D', 30], ['90D', 90]]
const KIND = { memory: 'Memory', architecture: 'Architecture' }

const Tip = ({ active, payload, label }) => active && payload?.length ? (
  <div className="glass-strong rounded-xl p-3 text-xs max-w-[200px]">
    <p className="text-titanium-300 mb-1 truncate">{label}</p>
    {payload.map(p => <p key={p.name} style={{ color: p.color || p.fill }}>{p.name}: {fmt(p.value)}</p>)}
  </div>
) : null

export default function Reports() {
  const [savings, setSavings] = useState({ verified: [], totalMonthlySavingPkr: 0 })
  const [breakdown, setBreakdown] = useState([])
  const [meta, setMeta] = useState({})
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [days, setDays] = useState(30)
  const [exportOpen, setExportOpen] = useState(false)

  const load = async (d = days) => {
    setLoading(true); setError('')
    try {
      const [s, b, h] = await Promise.all([reportsAPI.getSavings(), reportsAPI.getBreakdown(), reportsAPI.getHistory(d)])
      setSavings(s); setBreakdown(b.breakdown || []); setMeta({ source: b.source, warning: b.warning })
      setHistory((h.history || []).map(x => ({ time: new Date(x.at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }), cost: x.cost })))
    } catch {
      setError('Could not load reports. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  const pickRange = (d) => { setDays(d); load(d) }

  const items = savings.verified || []
  const verified = items.filter(i => i.status === 'verified')
  const waiting = items.filter(i => i.status === 'waiting')

  const exportCSV = () => {
    setExportOpen(false)
    downloadCSV('verified-savings.csv', items.map(i => ({
      function: i.function, change: `${KIND[i.kind] || i.kind}: ${i.oldValue} -> ${i.newValue}`, applied_at: i.takenAt, mode: i.mode,
      invocations_before: i.eventsBefore, invocations_after: i.eventsAfter, status: i.status,
      cost_per_invocation_before_pkr: i.costPerInvocationBefore ?? '', cost_per_invocation_after_pkr: i.costPerInvocationAfter ?? '',
      change_percent: i.changePct ?? '', monthly_saving_pkr: i.monthlySavingPkr ?? '',
    })))
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Reports &amp; Analytics</h1>
          <p className="text-xs text-titanium-500 mt-0.5">Savings measured from real billed durations before and after each applied change</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => load()} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100" aria-label="Refresh">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <div className="relative">
            <button onClick={() => setExportOpen(v => !v)} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
              <Download size={14} /> Export
            </button>
            {exportOpen && (
              <div className="absolute right-0 mt-2 w-52 rounded-xl p-2 z-10" style={{ background: '#0e1218', border: '1px solid rgba(255,255,255,0.1)' }}>
                <button onClick={exportCSV} disabled={!items.length} className="w-full flex items-center gap-2 text-xs text-titanium-300 hover:text-titanium-100 px-2 py-2 rounded-lg hover:bg-white/5 disabled:opacity-40">
                  <FileSpreadsheet size={14} /> Savings as CSV
                </button>
                <button onClick={() => { setExportOpen(false); window.print() }} className="w-full flex items-center gap-2 text-xs text-titanium-300 hover:text-titanium-100 px-2 py-2 rounded-lg hover:bg-white/5">
                  <FileText size={14} /> Print / Save as PDF
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}
      <SourceBanner source={meta.source} warning={meta.warning} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown size={14} className="text-success" />
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider">Verified Savings / Month</p>
          </div>
          <p className="text-2xl font-bold text-cyan-glow">{loading ? '...' : fmt(savings.totalMonthlySavingPkr)}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Verified Changes</p>
          <p className="text-2xl font-bold text-titanium-100">{loading ? '...' : verified.length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Waiting For Usage</p>
          <p className="text-2xl font-bold text-titanium-100">{loading ? '...' : waiting.length}</p>
        </div>
      </div>

      <div className="glass-card p-5">
        <h2 className="text-sm font-semibold text-titanium-100 mb-1">Verified Savings per Change</h2>
        <p className="text-xs text-titanium-500 mb-4">Billed cost per invocation before and after the change, from CloudWatch Logs. A result needs at least 20 invocations on each side.</p>
        {loading
          ? <div className="h-40 bg-white/5 rounded-xl animate-pulse" />
          : items.length === 0
            ? <p className="text-xs text-titanium-500 py-6 text-center">No change has been applied yet. Apply a recommendation on the Optimization page and let the function run.</p>
            : <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[720px]">
                  <thead>
                    <tr className="border-b border-white/8">
                      {['Function', 'Change', 'Invocations before / after', 'Cost per invocation (PKR)', 'Change', 'Saving / month'].map(h => (
                        <th key={h} className="px-3 py-2 text-left text-[11px] font-medium text-titanium-500 uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(i => (
                      <tr key={i.actionId} className="border-b border-white/5 last:border-0">
                        <td className="px-3 py-3 text-xs text-titanium-100 font-medium">{i.function}</td>
                        <td className="px-3 py-3 text-xs text-titanium-300">{KIND[i.kind] || i.kind}: {i.oldValue} → {i.newValue}</td>
                        <td className="px-3 py-3 text-xs text-titanium-700">{i.eventsBefore} / {i.eventsAfter}</td>
                        {i.status === 'verified' ? <>
                          <td className="px-3 py-3 text-xs text-titanium-300">{i.costPerInvocationBefore} → {i.costPerInvocationAfter}</td>
                          <td className="px-3 py-3 text-xs text-cyan-glow font-medium">{i.changePct}%</td>
                          <td className={`px-3 py-3 text-xs font-medium ${i.monthlySavingPkr > 0 ? 'text-success' : 'text-titanium-300'}`}>{fmt(i.monthlySavingPkr)}</td>
                        </> : <td colSpan={3} className="px-3 py-3 text-xs text-titanium-500">{i.message}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
        }
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-titanium-100 mb-1">Cost by Function</h2>
          <p className="text-xs text-titanium-500 mb-4">Estimated monthly PKR per Lambda function</p>
          {loading
            ? <div className="h-56 bg-white/5 rounded-xl animate-pulse" />
            : <ResponsiveContainer width="100%" height={220} minWidth={0}>
                <BarChart data={breakdown} margin={{ top: 5, right: 5, left: -15, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#7d8492', fontSize: 9 }} axisLine={false} tickLine={false} angle={-35} textAnchor="end" interval={0} />
                  <YAxis tick={{ fill: '#7d8492', fontSize: 10 }} axisLine={false} tickLine={false} width={40} />
                  <Tooltip content={<Tip />} />
                  <Bar dataKey="cost" name="Cost" radius={[5, 5, 0, 0]}>
                    {breakdown.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
          }
        </div>

        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-titanium-100 mb-1">Spend Distribution</h2>
          <p className="text-xs text-titanium-500 mb-4">Share of total estimated monthly cost</p>
          {loading
            ? <div className="h-56 bg-white/5 rounded-xl animate-pulse" />
            : <ResponsiveContainer width="100%" height={220} minWidth={0}>
                <PieChart>
                  <Pie data={breakdown} dataKey="cost" nameKey="name" cx="40%" cy="50%" innerRadius={50} outerRadius={78} paddingAngle={2}>
                    {breakdown.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />)}
                  </Pie>
                  <Tooltip content={<Tip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: '#7d8492' }} layout="vertical" align="right" verticalAlign="middle" />
                </PieChart>
              </ResponsiveContainer>
          }
        </div>
      </div>

      <div className="glass-card p-5">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
          <div>
            <h2 className="text-sm font-semibold text-titanium-100">Recorded Cost History</h2>
            <p className="text-xs text-titanium-500">One point per monitoring cycle</p>
          </div>
          <div className="flex items-center gap-1 glass-card p-1">
            {RANGES.map(([label, d]) => (
              <button key={label} onClick={() => pickRange(d)}
                className={`text-xs px-2.5 py-1.5 rounded-lg transition-colors ${days === d ? 'bg-cyan-glow/10 text-cyan-glow' : 'text-titanium-500 hover:text-titanium-100'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        {loading
          ? <div className="h-40 bg-white/5 rounded-xl animate-pulse" />
          : history.length < 2
            ? <p className="text-xs text-titanium-500 py-6 text-center">Not enough history yet. Each monitoring cycle adds one point.</p>
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
    </div>
  )
}
