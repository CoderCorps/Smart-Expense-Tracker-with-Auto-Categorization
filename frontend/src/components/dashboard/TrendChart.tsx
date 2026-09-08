import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatCurrency, formatMonthLabel } from '../../lib/format'
import type { TrendPoint } from '../../lib/types'
import { Card, EmptyState } from '../ui'

export function TrendChart({ data }: { data: TrendPoint[] }) {
  return (
    <Card>
      <h3 className="text-sm">Spend vs. earn over time</h3>
      {data.length === 0 ? (
        <div className="mt-4">
          <EmptyState title="Not enough data yet" hint="Trends appear once you have transactions across periods." />
        </div>
      ) : (
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="period"
                tickFormatter={formatMonthLabel}
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border-strong)' }}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => formatCurrency(v)}
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={64}
              />
              <Tooltip
                labelFormatter={(label) => formatMonthLabel(String(label))}
                formatter={(value) => formatCurrency(Number(value), true)}
                contentStyle={{
                  background: 'var(--surface-1)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
              <Line
                type="monotone"
                dataKey="total_spent"
                name="Spent"
                stroke="var(--series-2)"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
              <Line
                type="monotone"
                dataKey="total_earned"
                name="Earned"
                stroke="var(--series-1)"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}
