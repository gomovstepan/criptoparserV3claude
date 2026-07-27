import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { LineChart as LineChartIcon } from 'lucide-react'
import type { DailyPoint } from '../types'
import { formatDayMonth, formatUsd } from '../lib/format'
import { useChartTheme, tooltipStyle } from '../hooks/useChartTheme'
import EmptyState from './EmptyState'

/** Накопительный net P&L по дням (LineChart). */
export default function CumulativePnLChart({ data }: { data: DailyPoint[] }) {
  const t = useChartTheme()

  if (data.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center">
        <EmptyState
          compact
          icon={LineChartIcon}
          title="Нет сделок за период"
          hint="Выберите более длинный интервал в переключателе периода."
        />
      </div>
    )
  }

  const last = data[data.length - 1]?.cumulative_net_pnl ?? 0

  return (
    <div
      role="img"
      aria-label={`Накопительный чистый P&L по дням, ${data.length} дней. Итог: ${formatUsd(last)}.`}
    >
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }} accessibilityLayer>
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
          <ReferenceLine y={0} stroke={t.axis} strokeOpacity={0.5} />
          <Tooltip
            contentStyle={tooltipStyle(t)}
            labelFormatter={(v) => formatDayMonth(v as string)}
            formatter={(v: number) => [formatUsd(v), 'Накопленный net P&L']}
          />
          <Line
            type="monotone"
            dataKey="cumulative_net_pnl"
            stroke={t.accent}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
