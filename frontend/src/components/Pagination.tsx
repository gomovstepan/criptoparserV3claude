import { useId } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { formatCount } from '../lib/format'
import Button from './Button'

const PAGE_SIZES = [10, 25, 50, 100]

/** Навигация по страницам + выбор размера страницы. */
export default function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onPage,
  onPageSize,
}: {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPage: (p: number) => void
  onPageSize: (n: number) => void
}) {
  const id = useId()
  const pages = Math.max(totalPages, 1)

  return (
    <nav
      aria-label="Навигация по страницам"
      className="flex flex-wrap items-center justify-between gap-3 pt-3 text-sm"
    >
      <div className="flex items-center gap-2 text-muted">
        <label htmlFor={id}>Строк на странице</label>
        <select
          id={id}
          value={pageSize}
          onChange={(e) => onPageSize(Number(e.target.value))}
          className="min-h-[36px] rounded-lg border border-edge-strong bg-surface2 px-2 py-1 text-ink transition-colors duration-fast hover:border-accent"
        >
          {PAGE_SIZES.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <span className="ml-2">всего: {formatCount(total)}</span>
      </div>

      <div className="flex items-center gap-2">
        <Button size="sm" onClick={() => onPage(page - 1)} disabled={page <= 1} aria-label="Предыдущая страница">
          <ChevronLeft size={16} aria-hidden="true" /> Назад
        </Button>
        <span className="tabular-nums text-muted" aria-live="polite">
          {page} / {pages}
        </span>
        <Button
          size="sm"
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          aria-label="Следующая страница"
        >
          Вперёд <ChevronRight size={16} aria-hidden="true" />
        </Button>
      </div>
    </nav>
  )
}
