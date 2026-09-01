import { formatCurrency } from '../../lib/format'
import type { InsightAlert } from '../../lib/types'
import { Card, EmptyState } from '../ui'

export function InsightsList({ data }: { data: InsightAlert[] }) {
  return (
    <Card>
      <h3 className="text-sm">Insights</h3>
      {data.length === 0 ? (
        <div className="mt-4">
          <EmptyState title="Nothing unusual" hint="We'll flag categories that spike above your average." />
        </div>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {data.map((alert, i) => {
            const isWarning = alert.severity === 'warning'
            return (
              <li
                key={i}
                className={`flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-sm ${
                  isWarning
                    ? 'border-status-warning/30 bg-status-warning/10'
                    : 'border-border bg-surface-3'
                }`}
              >
                <span
                  aria-hidden
                  className={isWarning ? 'text-status-warning' : 'text-text-muted'}
                >
                  {isWarning ? '▲' : 'ⓘ'}
                </span>
                <div className="min-w-0">
                  <p className="font-medium text-text-primary">{alert.category_name}</p>
                  <p className="text-text-secondary">{alert.message}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {formatCurrency(alert.current_amount, true)} vs. avg {formatCurrency(alert.average_amount, true)}
                  </p>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}
