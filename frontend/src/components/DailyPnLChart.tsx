import { Bar, BarChart, Cell, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DailyPoint } from '../types'

/** Net P&L по дням (BarChart, зелёный/красный по знаку). */
export default function DailyPnLChart({ data }: { data: DailyPoint[] }) {
  if (data.length === 0) {
    return <div className="flex h-[240px] items-center justify-center text-sm text-muted">Нет данных</div>
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" vertical={false} />
        <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
        <YAxis stroke="#94a3b8" fontSize={11} width={60} tickLine={false} />
        <Tooltip
          cursor={{ fill: '#1a1a2e' }}
          contentStyle={{
            background: '#12121f',
            border: '1px solid #252540',
            borderRadius: 8,
            color: '#f1f5f9',
            fontSize: 12,
          }}
          formatter={(v: number) => [`$${v.toFixed(2)}`, 'Net P&L']}
        />
        <Bar dataKey="net_pnl" radius={[3, 3, 0, 0]} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.date} fill={d.net_pnl >= 0 ? '#22c55e' : '#ef4444'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
