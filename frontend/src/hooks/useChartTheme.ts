import { useMemo } from 'react'
import { useThemeStore } from '../store/themeStore'

export interface ChartTheme {
  accent: string
  success: string
  danger: string
  grid: string
  axis: string
  ink: string
  tooltipBg: string
  tooltipBorder: string
}

function readVar(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  const raw = styles.getPropertyValue(name).trim()
  return raw ? `rgb(${raw})` : fallback
}

/**
 * Цвета графиков из тех же CSS-переменных, что и остальной UI.
 *
 * Recharts принимает только литеральные цвета в props, поэтому раньше в каждом
 * графике были захардкожены значения тёмной темы (#12121f, #252540, #94a3b8).
 * В светлой теме это давало чёрные тултипы и почти невидимую сетку.
 * Пересчитывается при смене темы — `theme` в зависимостях не декоративен.
 */
export function useChartTheme(): ChartTheme {
  const theme = useThemeStore((s) => s.theme)

  return useMemo(() => {
    const styles = getComputedStyle(document.documentElement)
    return {
      accent: readVar(styles, '--c-accent', '#00d4aa'),
      success: readVar(styles, '--c-success', '#22c55e'),
      danger: readVar(styles, '--c-danger', '#ef4444'),
      grid: readVar(styles, '--c-grid', '#252540'),
      axis: readVar(styles, '--c-muted', '#94a3b8'),
      ink: readVar(styles, '--c-ink', '#f1f5f9'),
      tooltipBg: readVar(styles, '--c-surface', '#12121f'),
      tooltipBorder: readVar(styles, '--c-edge', '#252540'),
    }
    // theme — источник значений: смена класса на <html> меняет вычисленные переменные
  }, [theme])
}

/** Общий стиль всплывающей подсказки recharts. */
export function tooltipStyle(t: ChartTheme) {
  return {
    background: t.tooltipBg,
    border: `1px solid ${t.tooltipBorder}`,
    borderRadius: 8,
    color: t.ink,
    fontSize: 12,
    boxShadow: '0 8px 24px rgb(0 0 0 / 0.25)',
  }
}
