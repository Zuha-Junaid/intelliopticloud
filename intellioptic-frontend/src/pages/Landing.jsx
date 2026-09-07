import { Link } from 'react-router-dom'
import { Cloud, ArrowRight, TrendingDown, Zap, ShieldCheck, BarChart3, Check } from 'lucide-react'
 
const FEATURES = [
  { icon: Zap, title: 'Autonomous Optimization', desc: 'Fully automated cost reduction without manual input, running on a continuous 15-minute cycle.' },
  { icon: TrendingDown, title: 'AI-Based Decision Making', desc: 'XGBoost models trained on Google Colab predict optimal memory and instance configurations.' },
  { icon: ShieldCheck, title: 'Zero Downtime Execution', desc: 'Every optimization is validated and applied without interrupting your running services.' },
  { icon: BarChart3, title: 'Real-Time PKR Dashboards', desc: 'Localized cost tracking built specifically for Pakistani startups and SMEs.' },
]
 
const COMPETITORS = [
  { name: 'AWS Cost Explorer', limit: 'Requires manual analysis' },
  { name: 'CloudZero', limit: 'Over $10,000/month' },
  { name: 'Infracost', limit: 'Static insights only, no automation' },
]
 
export default function Landing() {
  return (
    <div className="aurora-bg min-h-screen flex flex-col">
      {/* Nav */}
      <header className="flex items-center justify-between px-4 sm:px-8 h-16 sm:h-20">
        <div className="flex items-center gap-2.5">
          <div
            style={{
              width: 34, height: 34, borderRadius: 9,
              background: 'linear-gradient(135deg, rgba(78,227,240,0.25), rgba(61,82,144,0.35))',
              border: '1px solid rgba(78,227,240,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}
          >
            <Cloud size={17} color="#4ee3f0" />
          </div>
          <span className="text-sm sm:text-base font-semibold text-titanium-100">IntelliOptiCloud</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link to="/login" className="text-xs sm:text-sm text-titanium-300 hover:text-titanium-100 px-2 sm:px-3 py-2">
            Log in
          </Link>
          <Link
            to="/register"
            className="text-xs sm:text-sm font-medium text-base-950 bg-cyan-glow hover:bg-cyan-soft px-3 sm:px-4 py-2 rounded-lg transition-colors"
          >
            Get Started
          </Link>
        </div>
      </header>
 
      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 sm:px-8 py-12 sm:py-16">
        <span className="cyan-badge mb-5 sm:mb-6">Production-Ready AI System</span>
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold text-titanium-100 max-w-3xl leading-tight">
          Cut your AWS bill by <span className="text-cyan-glow">60–70%</span> fully autonomously
        </h1>
        <p className="text-sm sm:text-base text-titanium-500 max-w-xl mt-5 sm:mt-6 px-2">
          IntelliOptiCloud monitors your AWS Lambda usage in real time and applies AI-driven
          cost optimizations with zero downtime, built free, for Pakistani startups and SMEs.
        </p>
        <div className="flex flex-col sm:flex-row items-center gap-3 mt-8 w-full sm:w-auto px-4 sm:px-0">
          <Link
            to="/register"
            className="w-full sm:w-auto flex items-center justify-center gap-2 text-sm font-medium text-base-950 bg-cyan-glow hover:bg-cyan-soft px-6 py-3 rounded-xl transition-colors"
          >
            Start Free <ArrowRight size={16} />
          </Link>
          <Link
            to="/login"
            className="w-full sm:w-auto flex items-center justify-center glass-card text-sm font-medium text-titanium-100 px-6 py-3 rounded-xl"
          >
            Log In
          </Link>
        </div>
 
        {/* Stat strip */}
        <div className="grid grid-cols-3 gap-4 sm:gap-10 mt-12 sm:mt-16 w-full max-w-lg px-4">
          <div>
            <p className="text-xl sm:text-3xl font-bold text-cyan-glow">64%</p>
            <p className="text-[10px] sm:text-xs text-titanium-500 mt-1">Avg. Cost Reduction</p>
          </div>
          <div>
            <p className="text-xl sm:text-3xl font-bold text-titanium-100">5,000+</p>
            <p className="text-[10px] sm:text-xs text-titanium-500 mt-1">Target Users</p>
          </div>
          <div>
            <p className="text-xl sm:text-3xl font-bold text-titanium-100">99.98%</p>
            <p className="text-[10px] sm:text-xs text-titanium-500 mt-1">Uptime</p>
          </div>
        </div>
      </section>
 
      {/* Features */}
      <section className="px-4 sm:px-8 py-12 sm:py-20 max-w-6xl mx-auto w-full">
        <h2 className="text-xl sm:text-2xl font-semibold text-titanium-100 text-center mb-2">
          Everything runs on autopilot
        </h2>
        <p className="text-xs sm:text-sm text-titanium-500 text-center mb-10 sm:mb-12">
          Built entirely on free-tier infrastructure AWS Free Tier
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5">
          {FEATURES.map((f) => (
            <div key={f.title} className="glass-card p-5 sm:p-6">
              <div
                style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: 'rgba(78,227,240,0.1)',
                  border: '1px solid rgba(78,227,240,0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}
                className="mb-4"
              >
                <f.icon size={19} color="#4ee3f0" />
              </div>
              <h3 className="text-sm font-semibold text-titanium-100 mb-1.5">{f.title}</h3>
              <p className="text-xs text-titanium-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
 
      {/* Competitive comparison */}
      <section className="px-4 sm:px-8 py-12 sm:py-20 max-w-4xl mx-auto w-full">
        <h2 className="text-xl sm:text-2xl font-semibold text-titanium-100 text-center mb-2">
          Why not the alternatives?
        </h2>
        <p className="text-xs sm:text-sm text-titanium-500 text-center mb-10">
          100% autonomous, real-time optimization using only free tools
        </p>
        <div className="glass-card overflow-hidden">
          {COMPETITORS.map((c, i) => (
            <div
              key={c.name}
              className={`flex items-center justify-between px-4 sm:px-6 py-4 ${i !== COMPETITORS.length - 1 ? 'border-b border-white/5' : ''}`}
            >
              <p className="text-xs sm:text-sm font-medium text-titanium-300">{c.name}</p>
              <p className="text-[11px] sm:text-xs text-titanium-700 text-right">{c.limit}</p>
            </div>
          ))}
          <div className="flex items-center justify-between px-4 sm:px-6 py-4 bg-cyan-glow/5 border-t border-cyan-glow/20">
            <p className="text-xs sm:text-sm font-semibold text-cyan-glow flex items-center gap-2">
              <Check size={14} /> IntelliOptiCloud
            </p>
            <p className="text-[11px] sm:text-xs text-cyan-glow text-right">Free, autonomous, zero setup</p>
          </div>
        </div>
      </section>
 
      {/* Footer CTA */}
      <section className="px-4 sm:px-8 py-12 sm:py-16 text-center">
        <h2 className="text-lg sm:text-2xl font-semibold text-titanium-100 mb-4">
          Ready to stop overpaying for AWS?
        </h2>
        <Link
          to="/register"
          className="inline-flex items-center justify-center gap-2 text-sm font-medium text-base-950 bg-cyan-glow hover:bg-cyan-soft px-6 py-3 rounded-xl transition-colors"
        >
          Create Free Account <ArrowRight size={16} />
        </Link>
        <p className="text-[11px] text-titanium-700 mt-8">
          IntelliOptiCloud Free Tier · Final Year Project · Department of Software Engineering, The University of Lahore
        </p>
      </section>
    </div>
  )
}