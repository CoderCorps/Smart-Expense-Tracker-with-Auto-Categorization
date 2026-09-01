import { useState, type FormEvent } from 'react'
import { apiErrorMessage } from '../../lib/api'
import { transactionsApi } from '../../lib/resources'
import type { Category, TransactionType } from '../../lib/types'
import { Button, ErrorBanner, Input, Label, Select } from '../ui'

export function AddTransactionModal({
  categories,
  onClose,
  onCreated,
}: {
  categories: Category[]
  onClose: () => void
  onCreated: () => void
}) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [type, setType] = useState<TransactionType>('spend')
  const [categoryId, setCategoryId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await transactionsApi.create({
        date,
        description,
        amount: Number(amount),
        type,
        category_id: categoryId ? Number(categoryId) : null,
      })
      onCreated()
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not add transaction.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-10 grid place-items-center bg-black/40 px-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl border border-border bg-surface-1 p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg">Add transaction</h2>
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
          {error && <ErrorBanner message={error} />}

          <div>
            <Label>Description</Label>
            <Input required value={description} onChange={(e) => setDescription(e.target.value)} autoFocus />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Date</Label>
              <Input type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div>
              <Label>Amount</Label>
              <Input type="number" step="0.01" min="0" required value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Type</Label>
              <Select value={type} onChange={(e) => setType(e.target.value as TransactionType)}>
                <option value="spend">Spend</option>
                <option value="earn">Earn</option>
              </Select>
            </div>
            <div>
              <Label>Category</Label>
              <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">Uncategorized</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Adding…' : 'Add transaction'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
