import { useState, useEffect, useMemo } from 'react'
import { Search, Filter, ArrowUpDown, Download, RefreshCw, ChevronRight } from 'lucide-react'
import { resourcesAPI } from '../lib/api'
import { fmtPKR as fmt, downloadCSV } from '../lib/format'
import SourceBanner from '../components/SourceBanner'

function StatusPill({ status }) {
  const map = { active: 'status-success', idle: 'status-pending' }
  const labels = { active: 'Active', idle: 'Idle (no invocations)' }
  return <span className={map[status] || 'status-pending'}>{labels[status] || status}</span>
}

const pct = (v) => (v === null || v === undefined ? 'n/a' : `${(v * 100).toFixed(1)}%`)
const mb = (v) => (v === null || v === undefined ? 'n/a' : `${v} MB`)

export default function Resources() {
  const [fns, setFns] = useState([])
  const [meta, setMeta] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('All')
  const [sort, setSort] = useState('monthlyCost')
  const [selected, setSelected] = useState(null)

  const load = async () => {
    setLoading(true); setError('')
    try {
      const r = await resourcesAPI.getFunctions()
      setFns(r.functions || []); setMeta({ source: r.source, warning: r.warning })
    } catch { setError('Failed to load. Is the backend running?') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const rows = useMemo(() => {
    let r = fns.filter(f => f.name.toLowerCase().includes(query.toLowerCase()))
    if (filter !== 'All') r = r.filter(f => f.status === filter.toLowerCase())
    return [...r].sort((a, b) => sort === 'name' ? a.name.localeCompare(b.name) : b[sort] - a[sort])
  }, [fns, query, filter, sort])

  const exportCSV = () => downloadCSV('lambda-functions.csv', rows.map(f => ({
    function: f.name, runtime: f.runtime, region: f.region, architecture: f.architecture, memory_mb: f.memory,
    peak_memory_mb: f.maxMemoryUsed ?? '', invocations_30d: f.invocations, avg_duration_ms: f.avgDuration,
    cold_start_ratio: f.coldStartRatio ?? '', monthly_cost_pkr: f.monthlyCost, status: f.status,
  })))

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Resources</h1>
          <p className="text-xs text-titanium-500 mt-0.5">AWS Lambda usage read from CloudWatch metrics and CloudWatch Logs (last 30 days; log details from the last 7 days)</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={exportCSV} disabled={!rows.length} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100 disabled:opacity-40">
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}
      <SourceBanner source={meta.source} warning={meta.warning} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="glass-card p-4"><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Functions</p><p className="text-xl font-bold text-titanium-100">{fns.length}</p></div>
        <div className="glass-card p-4"><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Estimated Monthly Cost</p><p className="text-xl font-bold text-cyan-glow">{fmt(fns.reduce((s, f) => s + f.monthlyCost, 0))}</p></div>
        <div className="glass-card p-4"><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Invocations (30 days)</p><p className="text-xl font-bold text-titanium-100">{fns.reduce((s, f) => s + f.invocations, 0).toLocaleString()}</p></div>
      </div>

      <div className="glass-card p-3 flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 flex-1 min-w-[180px]">
          <Search size={14} className="text-titanium-700 shrink-0" />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search functions..." className="bg-transparent outline-none text-sm text-titanium-100 placeholder:text-titanium-700 w-full" />
        </div>
        <div className="flex gap-1.5 overflow-x-auto">
          <Filter size={14} className="text-titanium-700 shrink-0 mt-1" />
          {['All', 'Active', 'Idle'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-lg border whitespace-nowrap ${filter === f ? 'border-cyan-glow/30 bg-cyan-glow/10 text-cyan-glow' : 'border-white/10 text-titanium-500'}`}>{f}</button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <ArrowUpDown size={14} className="text-titanium-700" />
          <select value={sort} onChange={e => setSort(e.target.value)} className="bg-white/5 border border-white/10 rounded-lg text-xs text-titanium-300 px-2 py-1.5 outline-none">
            <option value="monthlyCost" className="bg-base-900">Cost ↓</option>
            <option value="invocations" className="bg-base-900">Invocations</option>
            <option value="name" className="bg-base-900">Name A-Z</option>
          </select>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[760px]">
            <thead>
              <tr className="border-b border-white/8">
                {['Function', 'Arch', 'Memory (peak used)', 'Invocations', 'Avg duration', 'Cost/mo', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[11px] font-medium text-titanium-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array(5).fill(0).map((_, i) => (
                <tr key={i} className="border-b border-white/5">
                  {Array(7).fill(0).map((_, j) => <td key={j} className="px-4 py-3"><div className="h-3 bg-white/10 rounded animate-pulse w-16" /></td>)}
                </tr>
              )) : rows.map(fn => (
                <tr key={fn.id} onClick={() => setSelected(fn)} className="border-b border-white/5 last:border-0 hover:bg-white/4 cursor-pointer transition-colors">
                  <td className="px-4 py-3"><p className="text-xs font-medium text-titanium-100">{fn.name}</p><p className="text-[11px] text-titanium-700">{fn.runtime} · {fn.region}</p></td>
                  <td className="px-4 py-3 text-xs text-titanium-500">{fn.architecture}</td>
                  <td className="px-4 py-3 text-xs text-titanium-300">{fn.memory} MB <span className="text-titanium-700">({mb(fn.maxMemoryUsed)})</span></td>
                  <td className="px-4 py-3 text-xs text-titanium-300">{fn.invocations.toLocaleString()}</td>
                  <td className="px-4 py-3 text-xs text-titanium-300">{fn.avgDuration} ms</td>
                  <td className="px-4 py-3 text-xs font-medium text-titanium-100">{fmt(fn.monthlyCost)}</td>
                  <td className="px-4 py-3"><StatusPill status={fn.status} /></td>
                  <td className="px-4 py-3"><ChevronRight size={14} className="text-titanium-700" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!loading && rows.length === 0 && <div className="py-12 text-center"><p className="text-titanium-500 text-sm">No functions found.</p></div>}
      </div>

      {selected && (
        <div className="fixed inset-0 z-30 flex justify-end" onClick={() => setSelected(null)}>
          <div className="absolute inset-0 bg-black/60" />
          <div onClick={e => e.stopPropagation()} className="relative w-full sm:max-w-md h-full p-5 overflow-y-auto" style={{ background: '#0a0d12', borderLeft: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="flex items-center justify-between mb-5">
              <div><h2 className="text-sm font-semibold text-titanium-100">{selected.name}</h2><p className="text-[11px] text-titanium-500">{selected.region} · {selected.runtime}</p></div>
              <button onClick={() => setSelected(null)} className="text-xs text-titanium-500 border border-white/10 px-2 py-1 rounded">Close</button>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {[['Estimated cost / month', fmt(selected.monthlyCost), true], ['Invocations (30 d)', selected.invocations.toLocaleString(), false],
                ['Average duration', `${selected.avgDuration} ms`, false], ['Cold starts (7 d)', pct(selected.coldStartRatio), false],
                ['Configured memory', `${selected.memory} MB`, false], ['Peak memory used', mb(selected.maxMemoryUsed), false],
                ['Architecture', selected.architecture, false], ['Log samples read', selected.samples, false]].map(([l, v, c]) => (
                <div key={l} className="glass-card p-3"><p className="text-[11px] text-titanium-500 mb-1">{l}</p><p className={`text-base font-bold ${c ? 'text-cyan-glow' : 'text-titanium-100'}`}>{v}</p></div>
              ))}
            </div>
            <div className="glass-card p-4"><p className="text-xs font-medium text-titanium-100 mb-2">Status</p><StatusPill status={selected.status} />
              <p className="text-[11px] text-titanium-700 mt-2">Recommendations for this function are on the Optimization page.</p></div>
          </div>
        </div>
      )}
    </div>
  )
}
