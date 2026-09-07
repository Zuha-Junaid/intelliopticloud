import { useState, useEffect } from 'react'
import { Cpu, CheckCircle2, Loader2, Zap, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react'
import { optimizationAPI } from '../lib/api'

function PipelineStep({ step, isLast }) {
  const done = step.status === 'complete'
  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center shrink-0">
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: done ? 'rgba(61,220,151,0.12)' : 'rgba(78,227,240,0.12)',
          border: `1px solid ${done ? 'rgba(61,220,151,0.3)' : 'rgba(78,227,240,0.3)'}`
        }}>
          {done
            ? <CheckCircle2 size={14} color="#3ddc97" />
            : <Loader2 size={14} color="#4ee3f0" className="animate-spin" />}
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

export default function Optimization() {
  const [modelInfo, setModelInfo] = useState(null)
  const [pipeline, setPipeline] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retraining, setRetraining] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [info, pipe, recs] = await Promise.all([
        optimizationAPI.getModelInfo(),
        optimizationAPI.getPipeline(),
        optimizationAPI.getRecommendations(),
      ])
      setModelInfo(info)
      setPipeline(pipe.stages || [])
      setRecommendations(recs.recommendations || [])
    } catch {
      setError('Could not load optimization data. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const retrain = async () => {
    setRetraining(true)
    try {
      await optimizationAPI.retrain()
      await load()
    } finally {
      setRetraining(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="flex flex-col gap-5 animate-pulse">
      <div className="h-8 bg-white/10 rounded w-48" />
      <div className="glass-card h-40" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card h-64" />
        <div className="glass-card h-64" />
      </div>
    </div>
  )

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold text-titanium-100">Optimization Engine</h1>
          <p className="text-xs text-titanium-500 mt-0.5">AI-driven spot instance switching &amp; memory right-sizing</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-titanium-300 hover:text-titanium-100">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={retrain} disabled={retraining} className="glass-card flex items-center gap-2 px-3 py-2 text-xs text-cyan-glow hover:text-cyan-soft disabled:opacity-50">
            <Zap size={14} /> {retraining ? 'Retraining...' : 'Retrain Model'}
          </button>
        </div>
      </div>

      {error && <div className="glass-card p-3 border border-danger/20"><p className="text-xs text-danger">{error}</p></div>}

      {/* Model Info */}
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
            <span className="status-success">Model Active</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Accuracy</p><p className="text-lg font-bold text-cyan-glow">{modelInfo.accuracy}%</p></div>
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Version</p><p className="text-lg font-bold text-titanium-100">{modelInfo.version}</p></div>
            <div><p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1">Features</p><p className="text-lg font-bold text-titanium-100">{modelInfo.features?.length || 0}</p></div>
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
        {/* Pipeline */}
        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-titanium-100 mb-1">Live Optimization Pipeline</h2>
          <p className="text-xs text-titanium-500 mb-5">Runs autonomously every 15 minutes</p>
          {pipeline.map((step, i) => (
            <PipelineStep key={step.id} step={step} isLast={i === pipeline.length - 1} />
          ))}
        </div>

        {/* Recommendations */}
        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <Zap size={15} className="text-cyan-glow" />
            <h2 className="text-sm font-semibold text-titanium-100">AI Recommendations</h2>
          </div>
          <p className="text-xs text-titanium-500 mb-4">XGBoost predictions per function</p>
          <div className="flex flex-col gap-3 overflow-y-auto max-h-72">
            {recommendations.map(rec => (
              <div key={rec.function} className="border-b border-white/5 last:border-0 pb-3 last:pb-0">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs font-medium text-titanium-100 truncate mr-2">{rec.function}</p>
                  {rec.spot.recommend
                    ? <span className="status-success shrink-0">Spot -{rec.spot.saving_pct}%</span>
                    : <span className="status-pending shrink-0">On-Demand</span>}
                </div>
                <div className="flex items-center gap-2 text-[11px] text-titanium-700 flex-wrap">
                  <span>Memory: {rec.memory.current}MB</span>
                  <ArrowRight size={10} className="shrink-0" />
                  <span className="text-cyan-glow">{rec.memory.optimal}MB</span>
                  <span className="ml-auto">Confidence: {rec.memory.confidence}%</span>
                </div>
                {rec.memory.saves && (
                  <div style={{ marginTop: 6, height: 4, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                    <div style={{ width: `${rec.memory.confidence}%`, height: '100%', background: '#4ee3f0', borderRadius: 3 }} />
                  </div>
                )}
                <p className="text-[10px] mt-1 flex items-center gap-1" style={{ color: '#7d8492' }}>
                  <ShieldCheck size={10} /> Risk: {rec.spot.risk}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}