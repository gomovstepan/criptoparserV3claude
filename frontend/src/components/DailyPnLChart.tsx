import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { BarChart3 } from 'lucide-react'
import type { DailyPoint } from '../types'
import { formatDayMonth, formatUsd } from '../lib/format'
import { useChartTheme, tooltipStyle } from '../hooks/useChartTheme'
import EmptyState from './EmptyState'

/**
 * Net P&L по дням (BarChart, зелёный/красный по знаку).
 * Нулевая линия обязательна: без неё знак столбца читается только по цвету.
 */
export default function DailyPnLChart({ data }: { data: DailyPoint[] }) {
  const t = useChartTheme()

  if (data.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center">
        <EmptyState compact icon={BarChart3} title="Нет сделок за период" />
      </div>
    )
  }

  const profitable = data.filter((d) => d.net_pnl >= 0).length

  return (
    <div
      role="img"
      aria-label={`Чистый P&L по дням за ${data.length} дней: прибыльных дней ${profitable}, убыточных ${data.length - profitable}.`}
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }} accessibilityLayer>
          <CartesianGrid strokeDasharray="3 3" stroke={t.grid} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDayMonth}
            stroke={t.axis}
            fontSize={11}
            tickLine={false}
            minTickGap={20}
          />
          <YAxis
            stroke={t.axis}
            fontSize={11}
            width={72}
            tickLine={false}
            tickFormatter={(v: number) => formatUsd(v)}
          />
          <ReferenceLine y={0} stroke={t.axis} strokeOpacity={0.6} />
          <Tooltip
            cursor={{ fill: t.grid, fillOpacity: 0.4 }}
            contentStyle={tooltipStyle(t)}
            labelFormatter={(v) => formatDayMonth(v as string)}
            formatter={(v: number) => [formatUsd(v, true), 'Net P&L']}
          />
          <Bar dataKey="net_pnl" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.date} fill={d.net_pnl >= 0 ? t.success : t.danger} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
