import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  TrendingUp,
  ArrowLeftRight,
  BarChart3,
  Building2,
  Settings as SettingsIcon,
  X,
} from 'lucide-react'
import { cn } from '../lib/utils'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/opportunities', label: 'Opportunities', icon: TrendingUp },
  { to: '/trades', label: 'Trades', icon: ArrowLeftRight },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/exchanges', label: 'Exchanges', icon: Building2 },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <div className="flex h-14 items-center justify-between gap-2 border-b border-edge px-5">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="font-semibold tracking-tight text-ink">ArbitrageHub</span>
        </div>
        {onNavigate && (
          <button onClick={onNavigate} aria-label="Закрыть меню" className="text-muted hover:text-ink md:hidden">
            <X size={18} />
          </button>
        )}
      </div>
      <nav className="flex flex-col gap-1 p-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-accent/10 font-medium text-accent'
                  : 'text-muted hover:bg-surface2 hover:text-ink',
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}

/** Боковое меню. На desktop — статичная колонка; на mobile — выезжающий drawer. */
export default function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean
  onClose: () => void
}) {
  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-edge bg-surface md:flex">
        <NavContent />
      </aside>

      {/* Mobile drawer */}
      <div
        className={cn('fixed inset-0 z-40 md:hidden', mobileOpen ? '' : 'pointer-events-none')}
        aria-hidden={!mobileOpen}
      >
        <div
          className={cn(
            'absolute inset-0 bg-black/60 transition-opacity',
            mobileOpen ? 'opacity-100' : 'opacity-0',
          )}
          onClick={onClose}
        />
        <aside
          className={cn(
            'absolute left-0 top-0 flex h-full w-60 flex-col border-r border-edge bg-surface transition-transform',
            mobileOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <NavContent onNavigate={onClose} />
        </aside>
      </div>
    </>
  )
}
