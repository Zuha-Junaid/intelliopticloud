import { useState, useEffect } from 'react'
import { Cloud, CheckCircle2, Bell, User, Sliders, Zap, AlertTriangle } from 'lucide-react'
import { systemAPI, authAPI } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { timeAgo } from '../lib/format'

function Toggle({ checked, onChange, label }) {
  return (
    <button
      role="switch" aria-checked={checked} aria-label={label}
      onClick={() => onChange(!checked)}
      style={{
        width: 38, height: 22, borderRadius: 999,
        background: checked ? '#4ee3f0' : 'rgba(255,255,255,0.12)',
        position: 'relative', transition: 'background 0.2s ease', flexShrink: 0
      }}
    >
      <span style={{
        position: 'absolute', top: 2, left: checked ? 18 : 2, width: 18, height: 18, borderRadius: '50%',
        background: checked ? '#06070a' : '#b8bdc7', transition: 'left 0.2s ease'
      }} />
    </button>
  )
}

function Section({ icon: Icon, title, desc, children }) {
  return (
    <div className="glass-card p-4 sm:p-5">
      <div className="flex items-center gap-2.5 mb-1">
        <Icon size={16} className="text-cyan-glow shrink-0" />
        <h2 className="text-sm font-semibold text-titanium-100">{title}</h2>
      </div>
      <p className="text-xs text-titanium-500 mb-4">{desc}</p>
      {children}
    </div>
  )
}

export default function Settings() {
  const { user, updateUser } = useAuth()
  const [status, setStatus] = useState(null)
  const [cfg, setCfg] = useState(null)
  const [confidence, setConfidence] = useState(85)
  const [name, setName] = useState(user?.name || '')
  const [accountType, setAccountType] = useState(user?.accountType || 'Startup')
  const [msg, setMsg] = useState({ text: '', ok: true })

  const flash = (text, ok = true) => { setMsg({ text, ok }); setTimeout(() => setMsg({ text: '', ok: true }), 3500) }

  useEffect(() => {
    Promise.all([systemAPI.getStatus(), systemAPI.getSettings()])
      .then(([s, c]) => { setStatus(s); setCfg(c); setConfidence(c.min_confidence) })
      .catch(() => flash('Could not load settings. Is the backend running?', false))
  }, [])

  const save = async (changes) => {
    try { const c = await systemAPI.saveSettings(changes); setCfg(c); setConfidence(c.min_confidence); flash('Saved') }
    catch (e) { flash(e.message, false) }
  }

  const saveProfile = async () => {
    try { const r = await authAPI.updateMe({ name, accountType }); updateUser(r.user); flash('Profile saved') }
    catch (e) { flash(e.message, false) }
  }

  const live = status?.aws?.source === 'aws'

  return (
    <div className="flex flex-col gap-4 sm:gap-6 max-w-3xl">
      <div>
        <h1 className="text-lg sm:text-xl font-semibold text-titanium-100">Settings</h1>
        <p className="text-xs sm:text-sm text-titanium-500 mt-0.5">Connection status, autonomy level, notifications and your account</p>
      </div>

      {msg.text && (
        <div className="glass-card p-3" style={{ borderColor: msg.ok ? 'rgba(61,220,151,0.3)' : 'rgba(240,89,78,0.3)' }}>
          <p className={`text-xs ${msg.ok ? 'text-success' : 'text-danger'}`}>{msg.text}</p>
        </div>
      )}

      <Section icon={Cloud} title="AWS Connection" desc="Read from the server. AWS keys are server environment variables and are never stored in the browser.">
        {!status ? <p className="text-xs text-titanium-500">Loading...</p> : (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3 glass p-3 sm:p-4 rounded-xl">
              <div style={{ width: 36, height: 36, borderRadius: 9, background: live ? 'rgba(61,220,151,0.12)' : 'rgba(240,185,78,0.12)', border: `1px solid ${live ? 'rgba(61,220,151,0.25)' : 'rgba(240,185,78,0.25)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }} className="shrink-0">
                {live ? <CheckCircle2 size={17} color="#3ddc97" /> : <AlertTriangle size={17} color="#f0b94e" />}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-titanium-100">{live ? 'Connected to AWS' : 'Not connected: showing sample data'}</p>
                <p className="text-xs text-titanium-700 mt-0.5">Region {status.aws.region}{status.aws.warning ? ` · ${status.aws.warning}` : ''}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="glass-card p-3"><p className="text-titanium-500 text-[11px] mb-1">Applying changes</p><p className="text-titanium-100 font-medium">{status.apply.enabled ? 'Enabled' : 'Disabled'}</p></div>
              <div className="glass-card p-3"><p className="text-titanium-500 text-[11px] mb-1">Changeable functions</p><p className="text-titanium-100 font-medium">{status.apply.allowedPrefix}*</p></div>
              <div className="glass-card p-3"><p className="text-titanium-500 text-[11px] mb-1">Scheduled job</p><p className="text-titanium-100 font-medium">{status.schedulerConfigured ? 'Configured' : 'Not configured'}{status.lastCycle ? ` · last ${timeAgo(status.lastCycle.at)}` : ''}</p></div>
            </div>
          </div>
        )}
      </Section>

      <Section icon={Zap} title="Autonomy Level" desc="Controls what the optimization engine may do. Saved as soon as you choose.">
        <div className="flex flex-col gap-2">
          {[
            { key: 'auto', label: 'Automatic', sub: 'Each monitoring cycle applies safe memory changes by itself (confidence threshold, headroom check and allowed function names apply)' },
            { key: 'approve', label: 'Approve before applying', sub: 'Recommendations are shown; a change is applied only when you press Apply and confirm' },
            { key: 'monitor', label: 'Monitor only', sub: 'Show recommendations, never change anything' },
          ].map((opt) => (
            <label key={opt.key} className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${cfg?.autonomy === opt.key ? 'border-cyan-glow/30 bg-cyan-glow/5' : 'border-white/8 hover:border-white/15'}`}>
              <input type="radio" name="autonomy" checked={cfg?.autonomy === opt.key} onChange={() => save({ autonomy: opt.key })} className="accent-cyan-500 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-titanium-100">{opt.label}</p>
                <p className="text-[11px] text-titanium-700 mt-0.5">{opt.sub}</p>
              </div>
            </label>
          ))}
        </div>
      </Section>

      <Section icon={Bell} title="Notification Preferences" desc="Choose which notifications are created">
        <div className="flex flex-col gap-3">
          {[
            { key: 'notify_actions', label: 'Applied changes', sub: 'When a change is made on AWS or fails' },
            { key: 'notify_alerts', label: 'Recommendations and usage increases', sub: 'When a cycle finds a saving or a function is used much more' },
            { key: 'notify_summary', label: 'Weekly summary', sub: 'A short summary created by the monitoring cycle once a week' },
          ].map((p) => (
            <div key={p.key} className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-medium text-titanium-100">{p.label}</p>
                <p className="text-[11px] text-titanium-700 mt-0.5">{p.sub}</p>
              </div>
              <Toggle label={p.label} checked={!!cfg?.[p.key]} onChange={(v) => save({ [p.key]: v })} />
            </div>
          ))}
        </div>
      </Section>

      <Section icon={User} title="Account" desc="Your profile">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1.5">Full Name</p>
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-titanium-100 outline-none focus:border-cyan-glow/40" />
          </div>
          <div>
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1.5">Account Type</p>
            <select value={accountType} onChange={(e) => setAccountType(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-titanium-100 outline-none">
              {['Startup', 'SME', 'Enterprise'].map(t => <option key={t} className="bg-base-900">{t}</option>)}
            </select>
          </div>
        </div>
        <p className="text-[11px] text-titanium-700 mt-3">E-mail: {user?.email}</p>
        <button onClick={saveProfile} className="mt-4 text-xs font-medium text-base-950 bg-cyan-glow hover:bg-cyan-soft px-4 py-2 rounded-lg w-full sm:w-auto">
          Save Changes
        </button>
      </Section>

      <Section icon={Sliders} title="Automatic Change Threshold" desc="Used only in Automatic mode">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-titanium-300">Minimum model confidence to apply a change automatically</p>
          <span className="text-xs text-cyan-glow font-medium">{confidence}%</span>
        </div>
        <input type="range" min="50" max="100" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}
          onMouseUp={() => save({ min_confidence: confidence })} onTouchEnd={() => save({ min_confidence: confidence })}
          onKeyUp={() => save({ min_confidence: confidence })} className="w-full accent-cyan-500" />
      </Section>
    </div>
  )
}
