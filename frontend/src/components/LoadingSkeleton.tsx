import { cn } from '../lib/utils'

/** Базовый «пульсирующий» прямоугольник-заглушка. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-surface2', className)} />
}

/** Заглушка под сетку KPI-карточек. */
export function SkeletonCards({ count = 4 }: { count?: number }) {
  return (
    <div
      role="status"
      aria-label="Загрузка показателей"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-xl border border-edge bg-surface p-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-3 h-7 w-20" />
        </div>
      ))}
    </div>
  )
}

/** Заглушка под таблицу (строки). Резервирует высоту — контент не «прыгает». */
export function SkeletonTable({ rows = 6, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div role="status" aria-label="Загрузка данных" className="space-y-2">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cn('h-5 flex-1', c === 0 && 'max-w-[120px]')} />
          ))}
        </div>
      ))}
    </div>
  )
}
