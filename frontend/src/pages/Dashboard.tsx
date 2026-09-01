import { useEffect, useState } from 'react'
import { CategoryBreakdownChart } from '../components/dashboard/CategoryBreakdownChart'
import { InsightsList } from '../components/dashboard/InsightsList'
import { StatCard } from '../components/dashboard/StatCard'
import { TrendChart } from '../components/dashboard/TrendChart'
import { Input } from '../components/ui'
import { currentMonth } from '../lib/format'
import { dashboardApi } from '../lib/resources'
import type { CategoryBreakdownItem, DashboardSummary, InsightAlert, TrendPoint } from '../lib/types'

/**
 * Analytics endpoints (summary/category-breakdown/trends/insights) are
 * still stubs on the backend (raise NotImplementedError) — see
 * backend/app/services/analytics/aggregations.py. Each section below
 * fetches independently and falls back to a "not ready yet" placeholder
 * instead of failing the whole page.
 */
function NotReady({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-border bg-surface-1 px-4 py-8 text-center">
      <p className="text-sm font-medium text-text-primary">{label} isn't ready yet</p>
      <p className="text-xs text-text-muted">The analytics backend is still being built.</p>
    </div>
  )
}

export function Dashboard() {
  const [month, setMonth] = useState(currentMonth())

  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [summaryFailed, setSummaryFailed] = useState(false)

  const [breakdown, setBreakdown] = useState<CategoryBreakdownItem[] | null>(null)
  const [breakdownFailed, setBreakdownFailed] = useState(false)

  const [trends, setTrends] = useState<TrendPoint[] | null>(null)
  const [trendsFailed, setTrendsFailed] = useState(false)

  const [insights, setInsights] = useState<InsightAlert[] | null>(null)
  const [insightsFailed, setInsightsFailed] = useState(false)

  useEffect(() => {
    setSummary(null)
    setSummaryFailed(false)
    dashboardApi
      .summary(month)
      .then(setSummary)
      .catch(() => setSummaryFailed(true))
  }, [month])

  useEffect(() => {
    setBreakdown(null)
    setBreakdownFailed(false)
    dashboardApi
      .categoryBreakdown(month)
      .then(setBreakdown)
      .catch(() => setBreakdownFailed(true))
  }, [month])

  useEffect(() => {
    dashboardApi
      .trends('monthly')
      .then(setTrends)
      .catch(() => setTrendsFailed(true))
  }, [])

  useEffect(() => {
    dashboardApi
      .insights()
      .then(setInsights)
      .catch(() => setInsightsFailed(true))
  }, [])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl">Dashboard</h1>
          <p className="text-sm text-text-muted">Your spending overview</p>
        </div>
        <Input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="w-40"
        />
      </div>

      {summaryFailed ? (
        <NotReady label="Monthly summary" />
      ) : (
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Earned" amount={summary?.total_earned ?? 0} tone="good" />
          <StatCard label="Spent" amount={summary?.total_spent ?? 0} tone="bad" />
          <StatCard label="Balance" amount={summary?.balance ?? 0} />
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {breakdownFailed ? <NotReady label="Category breakdown" /> : <CategoryBreakdownChart data={breakdown ?? []} />}
        {trendsFailed ? <NotReady label="Trends" /> : <TrendChart data={trends ?? []} />}
      </div>

      {insightsFailed ? <NotReady label="Insights" /> : <InsightsList data={insights ?? []} />}
    </div>
  )
}
