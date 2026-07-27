import { useRef } from 'react'
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
import { useDialog } from '../hooks/useDialog'
import Button from './Button'

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
      <div className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-edge px-5">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-accent" aria-hidden="true" />
          <span className="font-semibold tracking-tight text-ink">ArbitrageHub</span>
        </div>
        {onNavigate && (
          <Button variant="ghost" size="icon" onClick={onNavigate} aria-label="Закрыть меню" className="md:hidden">
            <X size={18} aria-hidden="true" />
          </Button>
        )}
      </div>
      <nav aria-label="Основная навигация" className="flex flex-col gap-1 p-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-fast',
                isActive
                  ? 'bg-accent/10 font-medium text-accent'
                  : 'text-muted hover:bg-surface2 hover:text-ink',
              )
            }
          >
            <Icon size={18} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}

/**
 * Боковое меню. На desktop — статичная колонка; на mobile — выезжающий drawer.
 *
 * Закрытый drawer помечен `inert`: раньше он оставался в потоке фокуса, и
 * пользователь клавиатуры «проваливался» в невидимое меню. Плюс Esc, возврат
 * фокуса на кнопку-гамбургер и блокировка прокрутки фона (useDialog).
 */
export default function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean
  onClose: () => void
}) {
  const drawerRef = useRef<HTMLElement>(null)
  useDialog(mobileOpen, onClose, drawerRef)

  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-edge bg-surface md:flex">
        <NavContent />
      </aside>

      {/* Mobile drawer */}
      <div className={cn('fixed inset-0 z-drawer md:hidden', !mobileOpen && 'pointer-events-none')} inert={!mobileOpen}>
        <div
          aria-hidden="true"
          className={cn(
            'absolute inset-0 bg-black/60 transition-opacity duration-base',
            mobileOpen ? 'opacity-100' : 'opacity-0',
          )}
          onClick={onClose}
        />
        <aside
          ref={drawerRef}
          role="dialog"
          aria-modal="true"
          aria-label="Меню навигации"
          tabIndex={-1}
          className={cn(
            'absolute left-0 top-0 flex h-full w-60 flex-col overflow-y-auto border-r border-edge bg-surface outline-none transition-transform duration-base',
            mobileOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <NavContent onNavigate={onClose} />
        </aside>
      </div>
    </>
  )
}
