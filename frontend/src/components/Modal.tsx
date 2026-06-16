import type { ReactNode } from 'react'
import { X } from 'lucide-react'

/** Модальное окно с затемнением. Закрывается по клику на фон, крестик или Esc-кнопку. */
export default function Modal({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-edge bg-surface shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-edge px-5 py-3">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Закрыть"
            className="text-muted transition-colors hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4 text-sm text-muted">{children}</div>
        {footer && (
          <div className="flex justify-end gap-3 border-t border-edge px-5 py-3">{footer}</div>
        )}
      </div>
    </div>
  )
}
