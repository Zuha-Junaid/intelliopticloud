import { useState, useEffect } from 'react'
import { Cpu, CheckCircle2, Loader2, Zap, ArrowRight, ShieldCheck, RefreshCw, Clock, AlertTriangle, Undo2, Play } from 'lucide-react'
import { optimizationAPI, systemAPI } from '../lib/api'
import { timeAgo } from '../lib/format'
import SourceBanner from '../components/SourceBanner'

function PipelineStep({ step, isLast }) {
  const tone = {
    complete: { bg: 'rgba(61,220,151,0.12)', bd: 'rgba(61,220,151,0.3)', icon: <CheckCircle2 size={14} color="#3ddc97" /> },
    warning: { bg: 'rgba(240,185,78,0.12)', bd: 'rgba(240,185,78,0.3)', icon: <AlertTriangle size={14} color="#f0b94e" /> },
    waiting: { bg: 'rgba(125,132,146,0.12)', bd: 'rgba(125,132,146,0.3)', icon: <Clock size={14} color="#7d8492" /> },
  }[step.status] || { bg: 'rgba(78,227,240,0.12)', bd: 'rgba(78,227,240,0.3)', icon: <Loader2 size={14} color="#4ee3f0" className="animate-spin" /> }
  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center shrink-0">
        <div style={{ width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: tone.bg, border: `1px solid ${tone.bd}` }}>
          {tone.icon}
        </div>
        {!isLast && <div style={{ width: 1, height: 32, background: 'rgba(255,255,255,0.08)' }} />}
      </div>
      <div className="pb-6 min-w-0">
        <p className="text-xs font-medium text-titanium-100">{step.stage}</p>
        <p className="text-[11px] text-titanium-700 mt-0.5">{step.desc}</p>
      </div>
    </div>
  )
}

// One recommendation row with its Apply buttons and an inline confirmation step.
function RecCard({ rec, canApply, busy, onApply }) {
  const [pending, setPending] = useState(null)
  const m = rec.memory
  const ask = (kind, value, text) => setPending({ kind, value, text })
  const confirm = async () => { const p = pending; setPending(null); await onApply({ function: rec.function, kind: p.kind, value: p.value }) }

  return (
    <div className="border-b border-white/5 last:border-0 pb-3 last:pb-0">
      <div className="flex items-center justify-between mb-1 gap-2">
        <p className="text-xs font-medium text-titanium-100 truncate">{rec.function}</p>
        <span className="text-[10px] text-titanium-700 shrink-0">{rec.architecture}</span>
      </div>

      <div className="flex items-center gap-2 text-[11px] text-titanium-700 flex-wrap">
        <span>Memory: {m.current} MB</span>
        <ArrowRight size={10} className="shrink-0" />
        <span className={m.saves ? 'text-cyan-glow' : 'text-titanium-300'}>{m.optimal} MB</span>
        <span className="ml-auto">Confidence: {m.confidence}%</span>
      </div>
      <p className="text-[10px] mt-1" style={{ color: '#7d8492' }}>
        <ShieldCheck size={10} className="inline mr-1" />Basis: {m.basis}{m.saves ? ` · expected reduction ${m.reduction_pct}%` : ' · no change recommended'}
      </p>

      <div className="flex flex-wrap gap-2 mt-2 items-center">
        {m.saves && rec.measured && canApply(rec) && (
          <button disabled={busy} onClick={() => ask('memory', String(m.optimal), `Change ${rec.function} from ${m.current} MB to ${m.optimal} MB?`)}
            className="text-[11px] text-cyan-glow border border-cyan-glow/30 rounded-lg px-2.5 py-1 hover:bg-cyan-glow/10 disabled:opacity-40 flex items-center gap-1">
            <Play size={10} /> Apply {m.optimal} MB
          </button>
        )}
        {rec.arch.recommend && canApply(rec) && (
          <button disabled={busy} onClick={() => ask('architecture', 'arm64', `Switch ${rec.function} to arm64 (Graviton)? The same code is re-uploaded with the new architecture.`)}
            className="text-[11px] text-cyan-glow border border-cyan-glow/30 rounded-lg px-2.5 py-1 hover:bg-cyan-glow/10 disabled:opacity-40 flex items-center gap-1">
            <Play size={10} /> Switch to arm64 (-{rec.arch.saving_pct}%)
          </button>
        )}
        {rec.arch.recommend && !canApply(rec) && <span className="status-pending">arm64 would save {rec.arch.saving_pct}%</span>}
        {m.saves && !rec.measured && <span className="text-[10px] text-titanium-700">Run the function first: no measured memory use yet</span>}
        <span className="text-[10px] text-titanium-700" title="Advisory score from invocation volume and duration. AWS Lambda has no spot market.">
          Spot-suitability score {rec.spot.score}/80 ({rec.spot.risk} risk, advisory)
        </span>
      </div>

      {pending && (
        <div className="mt-2 p-2.5 rounded-lg" style={{ background: 'rgba(240,185,78,0.08)', border: '1px solid rgba(240,185,78,0.25)' }}>
          <p className="text-[11px] text-titanium-300 mb-2">{pending.text} This changes the function in your AWS account. You can roll it back below.</p>
          <div className="flex gap-2">
            <button onClick={confirm} className="text-[11px] font-medium text-base-950 bg-cyan-glow px-3 py-1 rounded-lg">Confirm</button>
            <button onClick={() => setPending(null)} className="text-[11px] text-titanium-300 border border-white/10 px-3 py-1 rounded-lg">Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Optimization() {
  const [modelInfo, setModelInfo] = useState(null)
  const [pipeline, setPipeline] = useState({ stages: [], lastCycle: null })
  const [recs, setRecs] = useState({ recommendations: [] })
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    setLoading(true); setError('')
    try {
      const [info, pipe, r, a] = await Promise.all([
        optimizationAPI.getModelInfo(), optimizationAPI.getPipeline(),
        optimizationAPI.getRecommendations(), optimizationAPI.getActions(),
      ])
      setModelInfo(info); setPipeline(pipe); setRecs(r); setActions(a.actions || [])
    } catch {
      setError('Could not load optimization data. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const run = async (fn, okText) => {
    setBusy(true); setError(''); setNotice('')
    try { await fn(); setNotice(okText); await load() }
    catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  const canApply = (rec) => recs.source === 'aws' && recs.applyEnabled && recs.autonomy !== 'monitor'
    && rec.function.startsWith(recs.allowedPrefix)

  const applyChange = (d) => run(() => optimizationAPI.apply(d), 'Change applied on AWS. Savings are verified after new invocations (see Reports).')
  const rollback = (id) => run(() => optimizationAPI.rollback(id), 'Change rolled back.')
  const runCycle = () => run(() => systemAPI.runCycle(), 'Monitoring cycle finished.')
  const retrain = () => run(() => optimizationAPI.retrain(), 'Model retrained.')

  if (loading && !modelInfo) return (
    <div className="flex flex-col gap-5 animate-pulse">
      <div className="h-8 bg-white/10 rounded w-48" />
      <div className="glass-card h-40" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4"><div className="glass-card h-64" /><div className="glass-card h-64" /></div>
    </div>
  )

  const held = modelInfo?.heldOut
  const applyOff = recs.source === 'aws' && !recs.applyEnabled

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Optimization Engine</h1>
          <p className="text-xs text-titanium-500 mt-0.5">Memory right-sizing and Graviton (arm64) switching, with safety checks, audit log and rollback</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={load} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={runCycle} disabled={busy} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-cyan-glow hover:text-cyan-soft disabled:opacity-50">
            <Play size={14} /> Run Cycle Now
          </button>
          <button onClick={retrain} disabled={busy} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-cyan-glow hover:text-cyan-soft disabled:opacity-50">
            <Zap size={14} /> Retrain Model
          </button>
        </div>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}
      {notice && <div className="glass-card p-3" style={{ borderColor: 'rgba(61,220,151,0.3)' }}><p className="text-xs text-success">{notice}</p></div>}
      <SourceBanner source={recs.source} warning={recs.warning} />
      {applyOff && <div className="glass-card p-3"><p className="text-xs text-titanium-300">Applying changes is switched off on the server (<code>APPLY_ENABLED</code>). Recommendations are shown but cannot be applied.</p></div>}
      {recs.source === 'aws' && recs.autonomy === 'monitor' && <div className="glass-card p-3"><p className="text-xs text-titanium-300">Autonomy level is <b>Monitor only</b>. Change it in Settings to apply changes.</p></div>}

      {modelInfo && (
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <div style={{ width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg,rgba(78,227,240,0.2),rgba(61,82,144,0.3))', border: '1px solid rgba(78,227,240,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Cpu size={18} color="#4ee3f0" />
              </div>
              <div>
                <p className="text-sm font-semibold text-titanium-100">{modelInfo.algorithm}</p>
                <p className="text-xs text-titanium-500">{modelInfo.trainedOn} · {modelInfo.version}</p>
              </div>
            </div>
            <span className="status-success">Model loaded</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">{held ? 'Held-out accuracy' : 'Accuracy (synthetic)'}</p><p className="text-lg font-bold text-cyan-glow">{modelInfo.accuracy}%</p></div>
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Within one size</p><p className="text-lg font-bold text-titanium-100">{held ? `${held.within_one_step_pct}%` : 'n/a'}</p></div>
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Extra cost vs best</p><p className="text-lg font-bold text-titanium-100">{held && held.mean_cost_regret_pct !== null ? `${held.mean_cost_regret_pct}%` : 'n/a'}</p></div>
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Source</p><p className="text-lg font-bold text-titanium-100">{modelInfo.source}</p></div>
          </div>

          <div className="border-t border-white/8 pt-3">
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-2">Input Features</p>
            <div className="flex flex-wrap gap-2">
              {(modelInfo.features || []).map(f => (
                <span key={f} className="text-[11px] text-titanium-300 bg-white/5 border border-white/8 rounded-full px-2.5 py-1">{f}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-titanium-100 mb-1">Last Monitoring Cycle</h2>
          <p className="text-xs text-titanium-500 mb-5">
            {pipeline.lastCycle ? `Ran ${timeAgo(pipeline.lastCycle.at)} (${pipeline.lastCycle.trigger}, ${pipeline.lastCycle.durationMs} ms)` : 'No cycle has run yet'}
          </p>
          {(pipeline.stages || []).map((step, i) => (
            <PipelineStep key={step.id} step={step} isLast={i === pipeline.stages.length - 1} />
          ))}
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <Zap size={15} className="text-cyan-glow" />
            <h2 className="text-sm font-semibold text-titanium-100">Recommendations</h2>
          </div>
          <p className="text-xs text-titanium-500 mb-4">XGBoost memory prediction per function. Only functions named <code>{recs.allowedPrefix}*</code> can be changed.</p>
          <div className="flex flex-col gap-3 overflow-y-auto max-h-[28rem]">
            {(recs.recommendations || []).map(rec => (
              <RecCard key={rec.function} rec={rec} canApply={canApply} busy={busy} onApply={applyChange} />
            ))}
            {!loading && (recs.recommendations || []).length === 0 && <p className="text-xs text-titanium-500">No Lambda functions found.</p>}
          </div>
        </div>
      </div>

      <div className="glass-card p-5">
        <h2 className="text-sm font-semibold text-titanium-100 mb-1">Change Log</h2>
        <p className="text-xs text-titanium-500 mb-4">Every change made or refused by the system, newest first</p>
        {actions.length === 0
          ? <p className="text-xs text-titanium-500 py-4 text-center">No changes have been made yet.</p>
          : <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[620px]">
                <thead>
                  <tr className="border-b border-white/8">
                    {['When', 'Function', 'Change', 'Mode', 'Result', ''].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-[11px] font-medium text-titanium-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {actions.map(a => (
                    <tr key={a.id} className="border-b border-white/5 last:border-0">
                      <td className="px-3 py-3 text-xs text-titanium-700">{timeAgo(a.takenAt)}</td>
                      <td className="px-3 py-3 text-xs text-titanium-100">{a.function}</td>
                      <td className="px-3 py-3 text-xs text-titanium-300">{a.kind}: {a.oldValue} → {a.newValue}</td>
                      <td className="px-3 py-3 text-xs text-titanium-500">{a.mode}</td>
                      <td className={`px-3 py-3 text-xs ${a.status === 'applied' ? 'text-success' : 'text-danger'}`}>{a.status}</td>
                      <td className="px-3 py-3">
                        {a.status === 'applied' && a.mode !== 'rollback' && (
                          <button disabled={busy} onClick={() => rollback(a.id)} className="text-[11px] text-titanium-300 border border-white/10 rounded-lg px-2 py-1 hover:text-titanium-100 disabled:opacity-40 flex items-center gap-1">
                            <Undo2 size={10} /> Roll back
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>}
      </div>
    </div>
  )
}
