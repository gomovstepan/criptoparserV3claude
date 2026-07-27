import { useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { useDialog } from '../hooks/useDialog'
import Button from './Button'

/**
 * Модальное окно.
 *
 * Было: `div` без ролей, закрытие только мышью, фокус оставался на странице
 * под затемнением, фон продолжал скроллиться.
 * Стало: role="dialog" + aria-modal, Esc, ловушка фокуса и его возврат на
 * триггер, блокировка прокрутки фона, рендер через портал (не обрезается
 * overflow-контейнерами).
 */
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
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

  useDialog(open, onClose, panelRef)

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-black/60 p-4 backdrop-blur-[2px]"
      // mousedown, а не click: иначе выделение текста внутри окна с отпусканием
      // мыши на затемнении закрывало бы окно
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="w-full max-w-md rounded-xl border border-edge bg-surface shadow-2xl outline-none"
      >
        <div className="flex items-center justify-between gap-3 border-b border-edge px-5 py-3">
          <h2 id={titleId} className="text-sm font-semibold text-ink">
            {title}
          </h2>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Закрыть окно">
            <X size={18} aria-hidden="true" />
          </Button>
        </div>
        <div className="px-5 py-4 text-sm text-ink">{children}</div>
        {footer && (
          <div className="flex flex-wrap justify-end gap-3 border-t border-edge px-5 py-3">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  )
}
