import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { PnLPoint } from '../types'

/** Накопительный P&L за период (AreaChart). */
export default function PnLChart({ data }: { data: PnLPoint[] }) {
  if (data.length === 0) {
    return <div className="flex h-[220px] items-center justify-center text-sm text-muted">Нет данных</div>
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d4aa" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#00d4aa" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" vertical={false} />
        <XAxis
          dataKey="time"
          tickFormatter={(t) => `${new Date(t).getHours()}:00`}
          stroke="#94a3b8"
          fontSize={11}
          tickLine={false}
        />
        <YAxis stroke="#94a3b8" fontSize={11} width={52} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: '#12121f',
            border: '1px solid #252540',
            borderRadius: 8,
            color: '#f1f5f9',
            fontSize: 12,
          }}
          labelFormatter={(t) => new Date(t).toLocaleString()}
          formatter={(v: number) => [`$${v.toFixed(2)}`, 'Cumulative P&L']}
        />
        <Area
          type="monotone"
          dataKey="cumulative"
          stroke="#00d4aa"
          strokeWidth={2}
          fill="url(#pnlGradient)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
