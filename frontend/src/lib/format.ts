const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

const currencyPrecise = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

export function formatCurrency(amount: number, precise = false): string {
  return precise ? currencyPrecise.format(amount) : currency.format(amount)
}

export function formatMonthLabel(period: string): string {
  // "2026-08" -> "Aug 2026", "2026-08-24" -> "Aug 24"
  const parts = period.split('-')
  const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2] ?? 1))
  return parts.length === 3
    ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

export function currentMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}
