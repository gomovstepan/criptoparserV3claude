import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { LineChart as LineChartIcon } from 'lucide-react'
import type { PnLPoint } from '../types'
import { formatDateTime, formatTime, formatUsd } from '../lib/format'
import { useChartTheme, tooltipStyle } from '../hooks/useChartTheme'
import EmptyState from './EmptyState'

/** Накопительный P&L за период (AreaChart). */
export default function PnLChart({ data }: { data: PnLPoint[] }) {
  const t = useChartTheme()

  if (data.length === 0) {
    return (
      <div className="flex h-[220px] items-center justify-center">
        <EmptyState
          compact
          icon={LineChartIcon}
          title="Нет данных за 24 часа"
          hint="График появится после первой закрытой сделки."
        />
      </div>
    )
  }

  const last = data[data.length - 1]?.cumulative ?? 0

  return (
    <div
      role="img"
      aria-label={`График накопительного P&L за 24 часа, ${data.length} точек. Итог: ${formatUsd(last)}.`}
    >
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }} accessibilityLayer>
          <defs>
            <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={t.accent} stopOpacity={0.35} />
              <stop offset="100%" stopColor={t.accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={t.grid} vertical={false} />
          <XAxis
            dataKey="time"
            tickFormatter={formatTime}
            stroke={t.axis}
            fontSize={11}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            stroke={t.axis}
            fontSize={11}
            width={64}
            tickLine={false}
            tickFormatter={(v: number) => formatUsd(v)}
          />
          <ReferenceLine y={0} stroke={t.axis} strokeOpacity={0.5} />
          <Tooltip
            contentStyle={tooltipStyle(t)}
            labelFormatter={(v) => formatDateTime(v as string)}
            formatter={(v: number) => [formatUsd(v), 'Накопленный P&L']}
          />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke={t.accent}
            strokeWidth={2}
            fill="url(#pnlGradient)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
