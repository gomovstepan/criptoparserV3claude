import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BarChart3 } from 'lucide-react'
import type { DailyPoint } from '../types'
import { formatCount, formatDayMonth } from '../lib/format'
import { useChartTheme, tooltipStyle } from '../hooks/useChartTheme'
import EmptyState from './EmptyState'

/** Количество сделок по дням (BarChart). */
export default function TradesPerDayChart({ data }: { data: DailyPoint[] }) {
  const t = useChartTheme()

  if (data.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center">
        <EmptyState compact icon={BarChart3} title="Нет сделок за период" />
      </div>
    )
  }

  const total = data.reduce((acc, d) => acc + d.trades, 0)

  return (
    <div role="img" aria-label={`Количество сделок по дням за ${data.length} дней, всего ${total}.`}>
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
          <YAxis stroke={t.axis} fontSize={11} width={48} tickLine={false} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: t.grid, fillOpacity: 0.4 }}
            contentStyle={tooltipStyle(t)}
            labelFormatter={(v) => formatDayMonth(v as string)}
            formatter={(v: number) => [formatCount(v), 'Сделок']}
          />
          <Bar dataKey="trades" fill={t.accent} radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
