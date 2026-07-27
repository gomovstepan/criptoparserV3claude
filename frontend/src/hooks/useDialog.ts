import { useEffect, useRef, type RefObject } from 'react'

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function focusableWithin(node: HTMLElement | null): HTMLElement[] {
  if (!node) return []
  return Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement,
  )
}

/**
 * Поведение модального слоя, обязательное по чек-листу доступности:
 * — Esc закрывает (`escape-routes`, `modal-escape`);
 * — фокус уходит внутрь при открытии и не выходит по Tab (`keyboard-nav`);
 * — фокус возвращается на элемент-триггер при закрытии (`focus-management`);
 * — фон не прокручивается под открытым слоем (`scroll-behavior`).
 *
 * Ничего из этого раньше не было: модалка закрывалась только мышью.
 */
export function useDialog(
  open: boolean,
  onClose: () => void,
  containerRef: RefObject<HTMLElement | null>,
) {
  // Через ref, чтобы новая функция onClose на каждом рендере не перезапускала эффект
  // (перезапуск воровал бы фокус у пользователя при каждом обновлении данных).
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  useEffect(() => {
    if (!open) return

    const trigger = document.activeElement as HTMLElement | null
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // Фокус внутрь — после того, как содержимое смонтировано.
    const raf = requestAnimationFrame(() => {
      const node = containerRef.current
      if (!node || node.contains(document.activeElement)) return
      ;(focusableWithin(node)[0] ?? node).focus()
    })

    const onKeyDown = (e: KeyboardEvent) => {
      const node = containerRef.current
      if (e.key === 'Escape') {
        e.stopPropagation()
        closeRef.current()
        return
      }
      if (e.key !== 'Tab' || !node) return
      const list = focusableWithin(node)
      if (list.length === 0) {
        e.preventDefault()
        node.focus()
        return
      }
      const first = list[0]
      const last = list[list.length - 1]
      const active = document.activeElement
      const outside = !node.contains(active)
      if (e.shiftKey && (active === first || outside)) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (active === last || outside)) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      cancelAnimationFrame(raf)
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.style.overflow = prevOverflow
      // Возвращаем фокус только если он всё ещё «внутри» закрываемого слоя,
      // иначе перехватили бы фокус, уже осознанно перемещённый пользователем.
      const active = document.activeElement
      const insideDialog = containerRef.current?.contains(active) ?? false
      if (trigger && document.contains(trigger) && (insideDialog || active === document.body)) {
        trigger.focus()
      }
    }
  }, [open, containerRef])
}
