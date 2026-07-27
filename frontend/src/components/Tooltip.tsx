import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'

/** Пузырь подсказки: позиционируется до отрисовки, поэтому не выезжает за экран. */
function Bubble({ anchor, text, id }: { anchor: DOMRect; text: string; id: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [style, setStyle] = useState<CSSProperties>({ left: 0, top: 0, visibility: 'hidden' })

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const { width, height } = el.getBoundingClientRect()
    const gap = 8
    const margin = 8
    const left = Math.min(
      Math.max(anchor.left + anchor.width / 2 - width / 2, margin),
      Math.max(margin, window.innerWidth - width - margin),
    )
    // Сверху, а если не помещается (первая строка таблицы, шапка) — снизу
    const above = anchor.top - height - gap
    const top = above >= margin ? above : anchor.bottom + gap
    setStyle({ left, top, visibility: 'visible' })
  }, [anchor])

  return createPortal(
    <div ref={ref} id={id} role="tooltip" className="tooltip-portal" style={style}>
      {text}
    </div>,
    document.body,
  )
}

/**
 * Подсказка-глоссарий.
 *
 * Было: только `onMouseEnter`/`onMouseLeave` на неинтерактивном span — контент
 * был недоступен с клавиатуры и с тач-устройств, а сам пузырь мог уехать за
 * границу экрана и «зависал» при скролле (position: fixed со старыми
 * координатами).
 *
 * Стало: hover (с задержкой 300ms), фокус с клавиатуры, тап по элементу,
 * закрытие по Escape и при скролле; связь с содержимым через aria-describedby.
 */
export default function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  const id = useId()
  const [anchor, setAnchor] = useState<DOMRect | null>(null)
  const ref = useRef<HTMLSpanElement>(null)
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearPending = () => {
    if (timeout.current) clearTimeout(timeout.current)
    timeout.current = null
  }

  const open = useCallback(() => {
    clearPending()
    if (ref.current) setAnchor(ref.current.getBoundingClientRect())
  }, [])

  const hide = useCallback(() => {
    clearPending()
    setAnchor(null)
  }, [])

  const openDelayed = useCallback(() => {
    clearPending()
    timeout.current = setTimeout(open, 300)
  }, [open])

  // Пузырь прибит к координатам вьюпорта — при скролле/ресайзе просто прячем его.
  useEffect(() => {
    if (!anchor) return
    window.addEventListener('scroll', hide, true)
    window.addEventListener('resize', hide)
    return () => {
      window.removeEventListener('scroll', hide, true)
      window.removeEventListener('resize', hide)
    }
  }, [anchor, hide])

  useEffect(() => clearPending, [])

  if (!text) return <>{children}</>

  return (
    <>
      <span
        ref={ref}
        tabIndex={0}
        aria-describedby={anchor ? id : undefined}
        onMouseEnter={openDelayed}
        onMouseLeave={hide}
        onFocus={open}
        onBlur={hide}
        onClick={() => (anchor ? hide() : open())}
        onKeyDown={(e) => {
          if (e.key === 'Escape') hide()
        }}
        className="inline-flex cursor-help rounded-sm border-b border-dashed border-muted/60"
      >
        {children}
      </span>
      {anchor && <Bubble anchor={anchor} text={text} id={id} />}
    </>
  )
}
