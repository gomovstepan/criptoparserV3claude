import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DailyPoint } from '../types'

/** Накопительный net P&L по дням (LineChart). */
export default function CumulativePnLChart({ data }: { data: DailyPoint[] }) {
  if (data.length === 0) {
    return <div className="flex h-[240px] items-center justify-center text-sm text-muted">Нет данных</div>
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" vertical={false} />
        <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
        <YAxis stroke="#94a3b8" fontSize={11} width={60} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: '#12121f',
            border: '1px solid #252540',
            borderRadius: 8,
            color: '#f1f5f9',
            fontSize: 12,
          }}
          formatter={(v: number) => [`$${v.toFixed(2)}`, 'Cumulative net P&L']}
        />
        <Line
          type="monotone"
          dataKey="cumulative_net_pnl"
          stroke="#00d4aa"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
