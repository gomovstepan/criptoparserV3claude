import type { ReactNode } from 'react'
import Tooltip from './Tooltip'

/** Карточка-секция с заголовком (контейнер для таблиц/графиков дашборда). */
export default function Panel({
  title,
  children,
  right,
  titleTooltip,
}: {
  title: string
  children: ReactNode
  right?: ReactNode
  titleTooltip?: string
}) {
  return (
    <div className="rounded-xl border border-edge bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">
          {titleTooltip ? <Tooltip text={titleTooltip}>{title}</Tooltip> : title}
        </h2>
        {right}
      </div>
      {children}
    </div>
  )
}
