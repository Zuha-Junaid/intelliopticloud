import { AlertTriangle } from 'lucide-react'

// Shown whenever the data on a page is the built-in sample and not read from AWS.
export default function SourceBanner({ source, warning }) {
  if (source !== 'sample') return null
  return (
    <div className="glass-card p-3 flex items-start gap-2" style={{ borderColor: 'rgba(240,185,78,0.3)' }}>
      <AlertTriangle size={15} color="#f0b94e" className="shrink-0 mt-0.5" />
      <p className="text-xs text-titanium-300">
        <span className="font-semibold" style={{ color: '#f0b94e' }}>Sample data. </span>
        {warning || 'AWS is not connected, so these numbers are examples and not your real usage.'}
      </p>
    </div>
  )
}
