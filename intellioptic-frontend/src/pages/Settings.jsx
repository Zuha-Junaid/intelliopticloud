import { useState } from 'react'
import { Cloud, CheckCircle2, Bell, User, Sliders, Zap, ExternalLink } from 'lucide-react'
 
function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      style={{
        width: 38, height: 22, borderRadius: 999,
        background: checked ? '#4ee3f0' : 'rgba(255,255,255,0.12)',
        position: 'relative', transition: 'background 0.2s ease', flexShrink: 0
      }}
    >
      <span
        style={{
          position: 'absolute', top: 2, left: checked ? 18 : 2,
          width: 18, height: 18, borderRadius: '50%',
          background: checked ? '#06070a' : '#b8bdc7',
          transition: 'left 0.2s ease'
        }}
      />
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
  const [connected, setConnected] = useState(true)
  const [prefs, setPrefs] = useState({
    optimizationAlerts: true,
    weeklyReports: true,
    concurrencyWarnings: true,
    emailDigest: false,
  })
  const [autonomy, setAutonomy] = useState('full')
 
  const togglePref = (key) => setPrefs((p) => ({ ...p, [key]: !p[key] }))
 
  return (
    <div className="flex flex-col gap-4 sm:gap-6 max-w-3xl">
      <div>
        <h1 className="text-lg sm:text-xl font-semibold text-titanium-100">Settings</h1>
        <p className="text-xs sm:text-sm text-titanium-500 mt-0.5">
          Account, AWS connection, and autonomous optimization preferences
        </p>
      </div>
 
      {/* AWS Connection */}
      <Section
        icon={Cloud}
        title="AWS Account Connection"
        desc="1-click deployment, no AWS expertise required"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 glass p-3 sm:p-4 rounded-xl">
          <div className="flex items-center gap-3 min-w-0">
            <div
              style={{
                width: 36, height: 36, borderRadius: 9,
                background: connected ? 'rgba(61,220,151,0.12)' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${connected ? 'rgba(61,220,151,0.25)' : 'rgba(255,255,255,0.1)'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}
              className="shrink-0"
            >
              {connected ? <CheckCircle2 size={17} color="#3ddc97" /> : <Cloud size={17} color="#7d8492" />}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-titanium-100 truncate">
                {connected ? 'Connected to AWS Free Tier' : 'Not connected'}
              </p>
              <p className="text-xs text-titanium-700 mt-0.5 truncate">
                {connected ? 'Account: 7012-xxxx-9931 · us-east-1' : 'Connect your AWS account to begin monitoring'}
              </p>
            </div>
          </div>
          <button
            onClick={() => setConnected((v) => !v)}
            className={`text-xs font-medium px-4 py-2 rounded-lg transition-colors shrink-0 ${
              connected
                ? 'text-danger bg-danger/10 border border-danger/20 hover:bg-danger/15'
                : 'text-base-950 bg-cyan-glow hover:bg-cyan-soft'
            }`}
          >
            {connected ? 'Disconnect' : 'Connect with AWS'}
          </button>
        </div>
        <a href="#" className="flex items-center gap-1.5 text-xs text-titanium-500 hover:text-cyan-glow mt-3">
          View CloudWatch IAM permissions required <ExternalLink size={11} />
        </a>
      </Section>
 
      {/* Autonomy level */}
      <Section
        icon={Zap}
        title="Autonomy Level"
        desc="Control how much the optimization engine can do without approval"
      >
        <div className="flex flex-col gap-2">
          {[
            { key: 'full', label: 'Fully Autonomous', sub: 'Apply all optimizations automatically, zero downtime' },
            { key: 'approve', label: 'Approve Before Applying', sub: 'Notify me and wait for approval before changes' },
            { key: 'monitor', label: 'Monitor Only', sub: 'Show recommendations, never apply changes' },
          ].map((opt) => (
            <label
              key={opt.key}
              className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${
                autonomy === opt.key ? 'border-cyan-glow/30 bg-cyan-glow/5' : 'border-white/8 hover:border-white/15'
              }`}
            >
              <input
                type="radio"
                checked={autonomy === opt.key}
                onChange={() => setAutonomy(opt.key)}
                className="accent-cyan-500 mt-0.5 shrink-0"
              />
              <div className="min-w-0">
                <p className="text-xs font-medium text-titanium-100">{opt.label}</p>
                <p className="text-[11px] text-titanium-700 mt-0.5">{opt.sub}</p>
              </div>
            </label>
          ))}
        </div>
      </Section>
 
      {/* Notification preferences */}
      <Section
        icon={Bell}
        title="Notification Preferences"
        desc="Choose what triggers an alert"
      >
        <div className="flex flex-col gap-3">
          {[
            { key: 'optimizationAlerts', label: 'Optimization actions', sub: 'When the engine applies a change' },
            { key: 'concurrencyWarnings', label: 'Concurrency recommendations', sub: 'Before enabling provisioned concurrency' },
            { key: 'weeklyReports', label: 'Weekly savings summary', sub: 'Every Monday at 9:00 AM' },
            { key: 'emailDigest', label: 'Email digest', sub: 'Daily email instead of in-app only' },
          ].map((p) => (
            <div key={p.key} className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-medium text-titanium-100">{p.label}</p>
                <p className="text-[11px] text-titanium-700 mt-0.5">{p.sub}</p>
              </div>
              <Toggle checked={prefs[p.key]} onChange={() => togglePref(p.key)} />
            </div>
          ))}
        </div>
      </Section>
 
      {/* Account */}
      <Section icon={User} title="Account" desc="Your profile and organization details">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1.5">Full Name</p>
            <input
              defaultValue="Zuha Junaid"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-titanium-100 outline-none focus:border-cyan-glow/40"
            />
          </div>
          <div>
            <p className="text-[11px] text-titanium-500 uppercase tracking-wider mb-1.5">Account Type</p>
            <select className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-titanium-100 outline-none">
              <option className="bg-base-900">Startup</option>
              <option className="bg-base-900">SME</option>
              <option className="bg-base-900">Enterprise</option>
            </select>
          </div>
        </div>
        <button className="mt-4 text-xs font-medium text-base-950 bg-cyan-glow hover:bg-cyan-soft px-4 py-2 rounded-lg w-full sm:w-auto">
          Save Changes
        </button>
      </Section>
 
      {/* Thresholds */}
      <Section icon={Sliders} title="Optimization Thresholds" desc="Fine-tune when the AI engine should act">
        <div className="flex flex-col gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-titanium-300">Minimum confidence to auto-apply</p>
              <span className="text-xs text-cyan-glow font-medium">85%</span>
            </div>
            <input type="range" min="50" max="100" defaultValue="85" className="w-full accent-cyan-500" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-titanium-300">Concurrency cost tolerance</p>
              <span className="text-xs text-cyan-glow font-medium">Medium</span>
            </div>
            <input type="range" min="0" max="2" defaultValue="1" className="w-full accent-cyan-500" />
          </div>
        </div>
      </Section>
    </div>
  )
}
