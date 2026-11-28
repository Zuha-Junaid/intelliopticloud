import { useState, useEffect } from 'react'
import { Activity } from 'lucide-react'
import { systemAPI } from '../../lib/api'

// Real status of the connection and of the autonomy level (read from the backend).
export default function EngineStatus({ strong = false }) {
  const [state, setState] = useState(null)

  useEffect(() => {
    let alive = true
    Promise.all([systemAPI.getStatus(), systemAPI.getSettings()])
      .then(([s, c]) => alive && setState({ s, c }))
      .catch(() => alive && setState(null))
    return () => { alive = false }
  }, [])

  const live = state?.s?.aws?.source === 'aws'
  const color = !state ? '#7d8492' : live ? '#3ddc97' : '#f0b94e'
  const mode = { monitor: 'Monitor only', approve: 'Approval mode', auto: 'Automatic mode' }[state?.c?.autonomy] || ''
  const title = !state ? 'Status unavailable' : live ? 'AWS connected' : 'Sample data'
  const sub = !state ? 'Backend not reachable' : `${mode}${state.s.apply.enabled ? '' : ' · apply disabled'}`

  return (
    <div style={{
      background: `${color}${strong ? '1a' : '12'}`, border: `1px solid ${color}33`, borderRadius: 12,
      padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexShrink: 0,
    }}>
      <Activity size={14} color={color} />
      <div>
        <p style={{ fontSize: 12, color, fontWeight: 600, margin: 0 }}>{title}</p>
        <p style={{ fontSize: 10, color: '#4a505c', marginTop: 1, marginBottom: 0 }}>{sub}</p>
      </div>
    </div>
  )
}
