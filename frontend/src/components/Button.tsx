import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import { cn } from '../lib/utils'

/**
 * Единая кнопка приложения.
 *
 * Собирает в одном месте то, что раньше дублировалось десятком инлайновых
 * наборов классов и местами терялось: видимый фокус, минимальный размер зоны
 * нажатия 44px, явное disabled-состояние и состояние загрузки (кнопка
 * блокируется на время запроса и сообщает об этом через aria-busy).
 *
 * Цвета текста берутся из пар `on-*`, поэтому контраст ≥4.5:1 в обеих темах.
 */
const button = cva(
  'inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-lg ' +
    'text-sm font-medium transition-colors duration-fast ' +
    'disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-on-accent hover:bg-accent/85',
        secondary: 'border border-edge-strong bg-surface2 text-ink hover:border-accent hover:bg-surface',
        ghost: 'text-muted hover:bg-surface2 hover:text-ink',
        danger: 'bg-danger text-on-danger hover:bg-danger/85',
        success: 'bg-success text-on-success hover:bg-success/85',
        dangerOutline: 'border border-danger/50 bg-surface2 text-danger hover:border-danger hover:bg-danger/10',
      },
      size: {
        // Высота 44px — минимальная зона нажатия по правилу touch-target-size
        md: 'min-h-[44px] px-4 py-2',
        // Компактный вариант в плотных панелях: визуально ниже, но зона нажатия
        // расширяется до 44px псевдоэлементом (.tap-target), без сдвига вёрстки
        sm: 'tap-target min-h-[34px] px-3 py-1.5',
        icon: 'tap-target h-9 w-9 shrink-0 p-0',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'color'>,
    VariantProps<typeof button> {
  loading?: boolean
  /** Текст, показываемый вместо children на время loading. */
  loadingText?: string
  children?: ReactNode
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, loading = false, loadingText, disabled, children, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(button({ variant, size }), className)}
      {...rest}
    >
      {loading && <Loader2 size={15} className="animate-spin" aria-hidden="true" />}
      {loading && loadingText ? loadingText : children}
    </button>
  )
})

export default Button
