import { cn } from '../lib/utils'

/**
 * Переключатель (switch). Управляемый: checked + onChange(boolean).
 * Визуально остаётся компактным (24×44), но зона нажатия расширена до 44×44
 * псевдоэлементом `.tap-target` — без изменения вёрстки таблицы.
 */
export default function Toggle({
  checked,
  onChange,
  disabled = false,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
  label?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'tap-target relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full',
        'transition-colors duration-fast',
        checked ? 'bg-accent' : 'bg-edge-strong',
        disabled && 'cursor-not-allowed opacity-50',
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-fast',
          checked ? 'translate-x-6' : 'translate-x-1',
        )}
      />
    </button>
  )
}
