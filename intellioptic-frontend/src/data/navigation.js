import {
  LayoutDashboard,
  Server,
  Cpu,
  BarChart3,
  Bell,
  Settings,
} from 'lucide-react'

export const navItems = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Resources', path: '/resources', icon: Server },
  { label: 'Optimization', path: '/optimization', icon: Cpu },
  { label: 'Reports', path: '/reports', icon: BarChart3 },
  { label: 'Notifications', path: '/notifications', icon: Bell },
  { label: 'Settings', path: '/settings', icon: Settings },
]