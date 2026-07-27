import { useId, type ReactNode } from 'react'
import Tooltip from './Tooltip'

/**
 * Карточка-секция с заголовком (контейнер для таблиц/графиков дашборда).
 * Отдаётся как <section aria-labelledby>, чтобы скринридер объявлял, к чему
 * относится содержимое, и секции можно было перебирать по регионам.
 */
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
  const id = useId()
  return (
    <section aria-labelledby={id} className="rounded-xl border border-edge bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id={id} className="text-sm font-semibold text-ink">
          {titleTooltip ? <Tooltip text={titleTooltip}>{title}</Tooltip> : title}
        </h2>
        {right}
      </div>
      {children}
    </section>
  )
}
