const BASE = "https://intelliopticloud.onrender.com/api";

function getToken() {
  try {
    const u = localStorage.getItem('ioc_user')
    return u ? JSON.parse(u).token : null
  } catch { return null }
}

async function req(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    const detail = Array.isArray(err.detail) ? 'Invalid input' : err.detail
    throw new Error(detail || 'Request failed')
  }
  return res.json()
}

const send = (method, body) => ({ method, body: JSON.stringify(body) })

export const authAPI = {
  register: (d) => req('/auth/register', send('POST', d)),
  login: (d) => req('/auth/login', send('POST', d)),
  updateMe: (d) => req('/auth/me', send('PUT', d)),
}

export const dashboardAPI = {
  getSummary: () => req('/dashboard/summary'),
}

export const resourcesAPI = {
  getFunctions: () => req('/resources/functions'),
  getFunction: (name) => req(`/resources/functions/${name}`),
}

export const optimizationAPI = {
  getModelInfo: () => req('/optimization/model-info'),
  getPipeline: () => req('/optimization/pipeline'),
  getRecommendations: () => req('/optimization/recommendations'),
  getActions: () => req('/optimization/actions'),
  apply: (d) => req('/optimization/apply', send('POST', { ...d, confirm: true })),
  rollback: (id) => req(`/optimization/rollback/${id}`, { method: 'POST' }),
  retrain: () => req('/optimization/retrain', { method: 'POST' }),
}

export const reportsAPI = {
  getSavings: () => req('/reports/savings'),
  getBreakdown: () => req('/reports/cost-breakdown'),
  getHistory: (days = 30) => req(`/reports/history?days=${days}`),
}

export const notificationsAPI = {
  getAll: () => req('/notifications/'),
  markRead: (id) => req(`/notifications/${id}/read`, { method: 'PUT' }),
  markAllRead: () => req('/notifications/read-all', { method: 'PUT' }),
}

export const systemAPI = {
  getStatus: () => req('/system/status'),
  runCycle: () => req('/system/run-cycle', { method: 'POST' }),
  getSettings: () => req('/settings'),
  saveSettings: (d) => req('/settings', send('PUT', d)),
}
