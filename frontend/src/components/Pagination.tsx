import { ChevronLeft, ChevronRight } from 'lucide-react'

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
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-3 text-sm">
      <div className="flex items-center gap-2 text-muted">
        <span>Строк на странице</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSize(Number(e.target.value))}
          className="rounded-lg border border-edge bg-surface2 px-2 py-1 text-ink outline-none focus:border-accent"
        >
          {PAGE_SIZES.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <span className="ml-2">всего: {total.toLocaleString()}</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
          className="flex items-center gap-1 rounded-lg border border-edge px-3 py-1.5 text-ink disabled:opacity-40 enabled:hover:bg-surface2"
        >
          <ChevronLeft size={16} /> Назад
        </button>
        <span className="text-muted">
          {page} / {Math.max(totalPages, 1)}
        </span>
        <button
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          className="flex items-center gap-1 rounded-lg border border-edge px-3 py-1.5 text-ink disabled:opacity-40 enabled:hover:bg-surface2"
        >
          Вперёд <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
