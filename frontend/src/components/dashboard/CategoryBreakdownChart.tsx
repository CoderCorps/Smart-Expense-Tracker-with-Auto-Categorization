import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { colorForCategory } from '../../lib/palette'
import { formatCurrency } from '../../lib/format'
import type { CategoryBreakdownItem } from '../../lib/types'
import { Card, EmptyState } from '../ui'

export function CategoryBreakdownChart({ data }: { data: CategoryBreakdownItem[] }) {
  const sorted = [...data].sort((a, b) => b.total_amount - a.total_amount)

  return (
    <Card>
      <h3 className="text-sm">Spending by category</h3>
      {sorted.length === 0 ? (
        <div className="mt-4">
          <EmptyState title="No spending yet" hint="Categorized transactions will show up here." />
        </div>
      ) : (
        <div className="mt-3" style={{ height: Math.max(sorted.length * 34, 120) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={sorted}
              layout="vertical"
              margin={{ top: 0, right: 24, bottom: 0, left: 0 }}
              barCategoryGap={8}
            >
              <CartesianGrid horizontal={false} stroke="var(--border)" />
              <XAxis
                type="number"
                tickFormatter={(v) => formatCurrency(v)}
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border-strong)' }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="category_name"
                width={130}
                tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: 'var(--surface-3)' }}
                contentStyle={{
                  background: 'var(--surface-1)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(value, _name, item) => [
                  `${formatCurrency(Number(value), true)} (${(item.payload as CategoryBreakdownItem).percentage.toFixed(1)}%)`,
                  'Spent',
                ]}
              />
              <Bar dataKey="total_amount" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {sorted.map((item) => (
                  <Cell key={item.category_name} fill={colorForCategory(item.category_name)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}
