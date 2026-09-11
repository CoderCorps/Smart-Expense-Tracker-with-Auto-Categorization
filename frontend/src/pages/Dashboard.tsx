import { CategoryBreakdownChart } from '../components/dashboard/CategoryBreakdownChart'
import { InsightsList } from '../components/dashboard/InsightsList'
import { StatCard } from '../components/dashboard/StatCard'
import { TrendChart } from '../components/dashboard/TrendChart'
import { Card, ErrorState, Input, Skeleton } from '../components/ui'
import { currentMonth, formatMonthLabel } from '../lib/format'
import { dashboardApi } from '../lib/resources'
import { useAsync } from '../lib/useAsync'
import { useState } from 'react'

/**
 * Each panel fetches independently, so one failing endpoint degrades that
 * panel rather than the page. Panels show a skeleton while loading and a
 * retry on failure — a zero is a real value here, and rendering one for
 * data that hasn't arrived (or didn't load) is a lie about the user's
 * money.
 */

function PanelSkeleton({ height = 'h-64' }: { height?: string }) {
  return (
    <Card>
      <Skeleton className="h-4 w-40" />
      <Skeleton className={`mt-4 w-full ${height}`} />
    </Card>
  )
}

export function Dashboard() {
  const [month, setMonth] = useState(currentMonth())

  const summary = useAsync(() => dashboardApi.summary(month), [month])
  const breakdown = useAsync(() => dashboardApi.categoryBreakdown(month), [month])
  const trends = useAsync(() => dashboardApi.trends('monthly'), [])
  const insights = useAsync(() => dashboardApi.insights(), [])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl">Dashboard</h1>
          <p className="text-sm text-text-muted">
            Your spending overview for {formatMonthLabel(month)}
          </p>
        </div>
        <Input
          type="month"
          aria-label="Month"
          value={month}
          onChange={(e) => setMonth(e.target.value || currentMonth())}
          className="w-44"
        />
      </div>

      {/* Summary */}
      {summary.error ? (
        <Card>
          <ErrorState message={summary.error} onRetry={summary.reload} />
        </Card>
      ) : summary.loading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <Skeleton className="h-3 w-16" />
              <Skeleton className="mt-3 h-8 w-28" />
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Earned" amount={summary.data?.total_earned ?? 0} tone="good" />
          <StatCard label="Spent" amount={summary.data?.total_spent ?? 0} tone="bad" />
          <StatCard
            label="Balance"
            amount={summary.data?.balance ?? 0}
            tone={(summary.data?.balance ?? 0) < 0 ? 'bad' : 'default'}
          />
        </div>
      )}

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        {breakdown.error ? (
          <Card>
            <h3 className="text-sm">Spending by category</h3>
            <ErrorState message={breakdown.error} onRetry={breakdown.reload} />
          </Card>
        ) : breakdown.loading ? (
          <PanelSkeleton />
        ) : (
          <CategoryBreakdownChart data={breakdown.data ?? []} />
        )}

        {trends.error ? (
          <Card>
            <h3 className="text-sm">Spend vs. earn over time</h3>
            <ErrorState message={trends.error} onRetry={trends.reload} />
          </Card>
        ) : trends.loading ? (
          <PanelSkeleton />
        ) : (
          <TrendChart data={trends.data ?? []} />
        )}
      </div>

      {/* Insights */}
      {insights.error ? (
        <Card>
          <h3 className="text-sm">Insights</h3>
          <ErrorState message={insights.error} onRetry={insights.reload} />
        </Card>
      ) : insights.loading ? (
        <PanelSkeleton height="h-20" />
      ) : (
        <InsightsList data={insights.data ?? []} />
      )}
    </div>
  )
}
