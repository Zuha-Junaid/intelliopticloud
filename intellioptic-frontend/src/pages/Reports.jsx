import { useState, useEffect } from 'react'
import { Download, TrendingDown, FileText, FileSpreadsheet, RefreshCw } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { reportsAPI } from '../lib/api'

const fmt = (n) => `PKR ${Number(n).toLocaleString()}`
const COLORS = ['#4ee3f0', '#3d5290', '#3ddc97', '#f0b94e', '#f0594e', '#7d8492', '#7ff0fa']
const RANGES = ['7D', '30D', '90D', '6M']

const Tip = ({ active, payload, label }) => active && payload?.length ? (
  <div className="glass-strong rounded-xl p-3 text-xs max-w-[200px]">
    <p className="text-titanium-300 mb-1 truncate">{label}</p>
    {payload.map(p => <p key={p.name} style={{ color: p.color || p.fill }}>{p.name}: {fmt(p.value)}</p>)}
  </div>
) : null

export default function Reports() {
  const [report, setReport] = useState([])
  const [breakdown, setBreakdown] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [range, setRange] = useState('6M')
  const [exportOpen, setExportOpen] = useState(false)

  const load = async () => {
    setLoading(true); setError('')
    try {
      const [s, b] = await Promise.all([reportsAPI.getSavings(), reportsAPI.getBreakdown()])
      setReport(s.report || [])
      setBreakdown(b.breakdown || [])
    } catch {
      setError('Could not load reports. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const totalSaved = report.reduce((s, m) => s + m.saved, 0)
  const avgReduction = report.length
    ? Math.round(report.reduce((s, m) => s + m.percentReduction, 0) / report.length)
    : 0

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Reports &amp; Analytics</h1>
          <p className="text-xs text-titanium-500 mt-0.5">Historical savings, cost breakdowns, and exportable summaries</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={load} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <div className="flex items-center gap-1 glass-card p-1">
            {RANGES.map(r => (
              <button key={r} onClick={() => setRange(r)}
                className={`text-xs px-2.5 py-1.5 rounded-lg transition-colors ${range === r ? 'bg-cyan-glow/10 text-cyan-glow' : 'text-titanium-500 hover:text-titanium-100'}`}>
                {r}
              </button>
            ))}
          </div>
          <div className="relative">
            <button onClick={() => setExportOpen(v => !v)} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
              <Download size={14} /> Export
            </button>
            {exportOpen && (
              <div className="absolute right-0 mt-2 w-44 rounded-xl p-2 z-10" style={{ background: '#0e1218', border: '1px solid rgba(255,255,255,0.1)' }}>
                <button className="w-full flex items-center gap-2 text-xs text-titanium-300 hover:text-titanium-100 px-2 py-2 rounded-lg hover:bg-white/5">
                  <FileSpreadsheet size={14} /> Export as CSV
                </button>
                <button className="w-full flex items-center gap-2 text-xs text-titanium-300 hover:text-titanium-100 px-2 py-2 rounded-lg hover:bg-white/5">
                  <FileText size={14} /> Export as PDF
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown size={14} className="text-success" />
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider">Total Saved</p>
          </div>
          <p className="text-2xl font-bold text-cyan-glow">{loading ? '...' : fmt(totalSaved)}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Avg Reduction</p>
          <p className="text-2xl font-bold text-titanium-100">{loading ? '...' : `${avgReduction}%`}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Months Tracked</p>
          <p className="text-2xl font-bold text-titanium-100">{loading ? '...' : report.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-titanium-100 mb-1">Cost by Function</h2>
          <p className="text-xs text-titanium-500 mb-4">Monthly PKR per Lambda function</p>
          {loading
            ? <div className="h-56 bg-white/5 rounded-xl animate-pulse" />
            : <ResponsiveContainer width="100%" height={220} minWidth={0}>
                <BarChart data={breakdown} margin={{ top: 5, right: 5, left: -15, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#7d8492', fontSize: 9 }} axisLine={false} tickLine={false} angle={-35} textAnchor="end" interval={0} />
                  <YAxis tick={{ fill: '#7d8492', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `${v/1000}k`} width={32} />
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
          <p className="text-xs text-titanium-500 mb-4">Share of total monthly cost</p>
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
        <h2 className="text-sm font-semibold text-titanium-100 mb-4">Monthly Savings Report</h2>
        {loading
          ? <div className="h-40 bg-white/5 rounded-xl animate-pulse" />
          : <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[460px]">
                <thead>
                  <tr className="border-b border-white/8">
                    {['Month', 'Before', 'After', 'Saved', '% Reduction'].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-[11px] font-medium text-titanium-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.map(m => (
                    <tr key={m.month} className="border-b border-white/5 last:border-0">
                      <td className="px-3 py-3 text-xs text-titanium-100 font-medium">{m.month}</td>
                      <td className="px-3 py-3 text-xs text-titanium-700">{fmt(m.before)}</td>
                      <td className="px-3 py-3 text-xs text-titanium-300">{fmt(m.after)}</td>
                      <td className="px-3 py-3 text-xs text-success font-medium">{fmt(m.saved)}</td>
                      <td className="px-3 py-3 text-xs text-cyan-glow font-medium">{m.percentReduction}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        }
      </div>
    </div>
  )
}