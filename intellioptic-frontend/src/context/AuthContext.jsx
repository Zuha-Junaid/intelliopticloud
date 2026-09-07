import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    try {
      const stored = localStorage.getItem('ioc_user')
      if (stored) setUser(JSON.parse(stored))
    } catch { localStorage.removeItem('ioc_user') }
    setLoading(false)
  }, [])

  const login = async ({ email, password }) => {
    try {
      const data = await authAPI.login({ email, password })
      const u = { ...data.user, token: data.access_token }
      localStorage.setItem('ioc_user', JSON.stringify(u))
      setUser(u)
      return { success: true }
    } catch (e) { return { success: false, error: e.message } }
  }

  const register = async ({ name, email, password, accountType }) => {
    try {
      const data = await authAPI.register({ name, email, password, accountType })
      const u = { ...data.user, token: data.access_token }
      localStorage.setItem('ioc_user', JSON.stringify(u))
      setUser(u)
      return { success: true }
    } catch (e) { return { success: false, error: e.message } }
  }

  const logout = () => {
    localStorage.removeItem('ioc_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}