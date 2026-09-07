const BASE = 'http://127.0.0.1:8000/api'

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
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const authAPI = {
  register: (d) => req('/auth/register', { method: 'POST', body: JSON.stringify(d) }),
  login: (d) => req('/auth/login', { method: 'POST', body: JSON.stringify(d) }),
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
  retrain: () => req('/optimization/retrain', { method: 'POST' }),
}

export const reportsAPI = {
  getSavings: () => req('/reports/savings'),
  getBreakdown: () => req('/reports/cost-breakdown'),
}

export const notificationsAPI = {
  getAll: () => req('/notifications/'),
  markRead: (id) => req(`/notifications/${id}/read`, { method: 'PUT' }),
  markAllRead: () => req('/notifications/read-all', { method: 'PUT' }),
}