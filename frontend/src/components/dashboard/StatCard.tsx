import { formatCurrency } from '../../lib/format'
import { Card } from '../ui'

export function StatCard({
  label,
  amount,
  tone = 'default',
}: {
  label: string
  amount: number
  tone?: 'default' | 'good' | 'bad'
}) {
  const toneClass =
    tone === 'good' ? 'text-[var(--success-text)]' : tone === 'bad' ? 'text-status-critical' : 'text-text-primary'

  return (
    <Card>
      <p className="text-xs font-medium text-text-muted">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${toneClass}`}>{formatCurrency(amount)}</p>
    </Card>
  )
}
