import { useEffect, useState } from 'react'
import { AddTransactionModal } from '../components/transactions/AddTransactionModal'
import { Badge, Button, EmptyState, ErrorBanner, Input, Select, Spinner } from '../components/ui'
import { apiErrorMessage } from '../lib/api'
import { formatCurrency } from '../lib/format'
import { categoriesApi, transactionsApi } from '../lib/resources'
import type { Category, Transaction, TransactionType } from '../lib/types'

const PAGE_SIZE = 25

export function Transactions() {
  const [categories, setCategories] = useState<Category[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [type, setType] = useState<TransactionType | ''>('')
  const [categoryId, setCategoryId] = useState('')
  const [page, setPage] = useState(1)
  const [showAdd, setShowAdd] = useState(false)

  useEffect(() => {
    categoriesApi.list().then(setCategories).catch(() => {})
  }, [])

  function load() {
    setLoading(true)
    setError(null)
    transactionsApi
      .list({
        search: search || undefined,
        type: type || undefined,
        category_id: categoryId ? Number(categoryId) : undefined,
        page,
        page_size: PAGE_SIZE,
      })
      .then(setTransactions)
      .catch((err) => setError(apiErrorMessage(err, 'Could not load transactions.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [search, type, categoryId, page])

  async function handleCategoryChange(txnId: number, newCategoryId: string) {
    if (!newCategoryId) return
    const previous = transactions
    setTransactions((rows) =>
      rows.map((t) =>
        t.id === txnId
          ? {
              ...t,
              category_id: Number(newCategoryId),
              category_name: categories.find((c) => c.id === Number(newCategoryId))?.name ?? null,
              category_source: 'manual_correction',
            }
          : t,
      ),
    )
    try {
      await transactionsApi.updateCategory(txnId, Number(newCategoryId))
    } catch {
      setTransactions(previous)
    }
  }

  async function handleDelete(txnId: number) {
    if (!confirm('Delete this transaction?')) return
    const previous = transactions
    setTransactions((rows) => rows.filter((t) => t.id !== txnId))
    try {
      await transactionsApi.remove(txnId)
    } catch {
      setTransactions(previous)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl">Transactions</h1>
          <p className="text-sm text-text-muted">Browse, filter, and correct categories</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>+ Add transaction</Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search description…"
          value={search}
          onChange={(e) => {
            setPage(1)
            setSearch(e.target.value)
          }}
          className="max-w-xs"
        />
        <Select
          value={type}
          onChange={(e) => {
            setPage(1)
            setType(e.target.value as TransactionType | '')
          }}
          className="w-36"
        >
          <option value="">All types</option>
          <option value="spend">Spend</option>
          <option value="earn">Earn</option>
        </Select>
        <Select
          value={categoryId}
          onChange={(e) => {
            setPage(1)
            setCategoryId(e.target.value)
          }}
          className="w-48"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="overflow-hidden rounded-xl border border-border bg-surface-1">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-3 text-xs font-medium text-text-muted">
              <th className="px-4 py-2.5">Date</th>
              <th className="px-4 py-2.5">Description</th>
              <th className="px-4 py-2.5">Category</th>
              <th className="px-4 py-2.5">Source</th>
              <th className="px-4 py-2.5 text-right">Amount</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="py-10">
                  <div className="flex justify-center">
                    <Spinner className="h-5 w-5" />
                  </div>
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-10">
                  <EmptyState title="No transactions found" hint="Try adjusting your filters, or add one manually." />
                </td>
              </tr>
            ) : (
              transactions.map((t) => (
                <tr key={t.id} className="border-b border-border last:border-0 hover:bg-surface-3/50">
                  <td className="whitespace-nowrap px-4 py-2.5 text-text-secondary">{t.date}</td>
                  <td className="px-4 py-2.5 text-text-primary">{t.description}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5">
                      <select
                        value={t.category_id ?? ''}
                        onChange={(e) => handleCategoryChange(t.id, e.target.value)}
                        className="rounded-md border border-transparent bg-transparent px-1 py-0.5 text-sm text-text-secondary hover:border-border focus:border-series-1 focus:outline-none"
                      >
                        <option value="">Uncategorized</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                      {t.category_source === 'manual_correction' && <Badge>edited</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge>{t.source}</Badge>
                  </td>
                  <td
                    className={`whitespace-nowrap px-4 py-2.5 text-right font-medium tabular-nums ${
                      t.type === 'earn' ? 'text-[var(--success-text)]' : 'text-text-primary'
                    }`}
                  >
                    {t.type === 'earn' ? '+' : '-'}
                    {formatCurrency(t.amount, true)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => handleDelete(t.id)}
                      className="text-xs text-text-muted hover:text-status-critical"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-text-muted">Page {page}</p>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button
            variant="secondary"
            disabled={transactions.length < PAGE_SIZE}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      {showAdd && (
        <AddTransactionModal
          categories={categories}
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false)
            load()
          }}
        />
      )}
    </div>
  )
}
