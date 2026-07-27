import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Объединение классов Tailwind с разрешением конфликтов. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/**
 * Массив из ответа API или пустой массив.
 *
 * Раньше значения вида `res.data.items` клались в state как есть: стоило
 * ответу прийти неожиданной формы (прокси вернул HTML, поле переименовали),
 * как следующий `.map()`/`.length` ронял всю страницу в ErrorBoundary.
 * Отсутствие данных должно приводить к пустому состоянию, а не к белому экрану.
 */
export function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

/** Число из ответа API или значение по умолчанию. */
export function asNumber(value: unknown, fallback = 0): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : fallback
}
