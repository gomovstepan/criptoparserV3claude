import { useState, useRef, useCallback, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface TooltipProps {
  text: string
  children: ReactNode
}

export default function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const ref = useRef<HTMLSpanElement>(null)
  const timeout = useRef<ReturnType<typeof setTimeout>>(null)

  const show = useCallback(() => {
    if (timeout.current) clearTimeout(timeout.current)
    timeout.current = setTimeout(() => {
      if (!ref.current) return
      const r = ref.current.getBoundingClientRect()
      setPos({ x: r.left + r.width / 2, y: r.top })
      setVisible(true)
    }, 300)
  }, [])

  const hide = useCallback(() => {
    if (timeout.current) clearTimeout(timeout.current)
    timeout.current = null
    setVisible(false)
  }, [])

  return (
    <>
      <span
        ref={ref}
        onMouseEnter={show}
        onMouseLeave={hide}
        className="inline-flex cursor-help border-b border-dashed border-muted/40"
      >
        {children}
      </span>
      {visible &&
        createPortal(
          <div
            role="tooltip"
            className="tooltip-portal"
            style={{ left: pos.x, top: pos.y }}
          >
            {text}
          </div>,
          document.body,
        )}
    </>
  )
}
