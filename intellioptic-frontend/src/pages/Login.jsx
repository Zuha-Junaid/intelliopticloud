import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Cloud, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setServerError('')
    const newErrors = {}
    if (!email) newErrors.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(email)) newErrors.email = 'Enter a valid email address'
    if (!password) newErrors.password = 'Password is required'
    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) return

    setLoading(true)
    const result = await login({ email, password })
    setLoading(false)

    if (result.success) {
      navigate('/')
    } else {
      setServerError(result.error || 'Invalid email or password')
    }
  }

  return (
    <div className="aurora-bg min-h-screen flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: 'linear-gradient(135deg, rgba(78,227,240,0.25), rgba(61,82,144,0.35))',
              border: '1px solid rgba(78,227,240,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}
            className="mb-4"
          >
            <Cloud size={22} color="#4ee3f0" />
          </div>
          <h1 className="text-lg font-semibold text-titanium-100">Welcome back</h1>
          <p className="text-xs text-titanium-500 mt-1 text-center">
            Log in to your IntelliOptiCloud dashboard
          </p>
        </div>

        <div className="glass-card p-5 sm:p-6">
          {serverError && (
            <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/20">
              <p className="text-xs text-danger">{serverError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="text-xs font-medium text-titanium-300 mb-1.5 block">Email</label>
              <div className={`flex items-center gap-2 bg-white/5 border rounded-lg px-3 py-2.5 ${errors.email ? 'border-danger/50' : 'border-white/10'}`}>
                <Mail size={15} className="text-titanium-700 shrink-0" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@startup.com"
                  className="bg-transparent outline-none text-sm text-titanium-100 placeholder:text-titanium-700 w-full"
                />
              </div>
              {errors.email && <p className="text-[11px] text-danger mt-1">{errors.email}</p>}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-titanium-300">Password</label>
                <a href="#" className="text-[11px] text-cyan-glow hover:text-cyan-soft">Forgot password?</a>
              </div>
              <div className={`flex items-center gap-2 bg-white/5 border rounded-lg px-3 py-2.5 ${errors.password ? 'border-danger/50' : 'border-white/10'}`}>
                <Lock size={15} className="text-titanium-700 shrink-0" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="bg-transparent outline-none text-sm text-titanium-100 placeholder:text-titanium-700 w-full"
                />
                <button type="button" onClick={() => setShowPassword((v) => !v)} className="shrink-0">
                  {showPassword ? <EyeOff size={15} className="text-titanium-700" /> : <Eye size={15} className="text-titanium-700" />}
                </button>
              </div>
              {errors.password && <p className="text-[11px] text-danger mt-1">{errors.password}</p>}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-2 text-sm font-medium text-base-950 bg-cyan-glow hover:bg-cyan-soft px-4 py-2.5 rounded-lg transition-colors mt-1 disabled:opacity-60"
            >
              {loading ? 'Logging in...' : <><span>Log In</span> <ArrowRight size={15} /></>}
            </button>
          </form>
        </div>

        <p className="text-xs text-titanium-500 text-center mt-6">
          Don't have an account?{' '}
          <Link to="/register" className="text-cyan-glow hover:text-cyan-soft font-medium">
            Create one free
          </Link>
        </p>
      </div>
    </div>
  )
}