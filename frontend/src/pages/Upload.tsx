import { useRef, useState } from 'react'
import { Button, Card, ErrorBanner, Select, Spinner } from '../components/ui'
import { apiErrorMessage } from '../lib/api'
import { uploadApi } from '../lib/resources'
import { STANDARD_FIELDS, type ColumnMappingSuggestion, type UploadResult } from '../lib/types'

export function Upload() {
  const fileInput = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<ColumnMappingSuggestion | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [result, setResult] = useState<UploadResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setResult(null)
    setLoading(true)
    try {
      const suggestion = await uploadApi.preview(file)
      setPreview(suggestion)
      setMapping(
        Object.fromEntries(
          STANDARD_FIELDS.map((field) => [field, suggestion.mapping[field] ?? '']),
        ),
      )
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not read that file.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm() {
    if (!preview) return
    const missing = STANDARD_FIELDS.filter((f) => !mapping[f])
    if (missing.length > 0) {
      setError(`Please map: ${missing.join(', ')}`)
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await uploadApi.confirm(preview.upload_id, mapping)
      setResult(res)
      setPreview(null)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not save the file.'))
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setPreview(null)
    setResult(null)
    setError(null)
    if (fileInput.current) fileInput.current.value = ''
  }

  return (
    <div className="flex max-w-2xl flex-col gap-5">
      <div>
        <h1 className="text-xl">Upload transactions</h1>
        <p className="text-sm text-text-muted">Import a CSV or PDF statement — PDF parsing is still a work in progress.</p>
      </div>

      {error && <ErrorBanner message={error} />}

      {!preview && !result && (
        <Card>
          <label
            htmlFor="file"
            className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-10 text-center hover:bg-surface-3"
          >
            <span className="text-2xl" aria-hidden>
              ⇧
            </span>
            <span className="text-sm font-medium text-text-primary">
              {loading ? 'Reading file…' : 'Click to choose a .csv or .pdf file'}
            </span>
            <span className="text-xs text-text-muted">We'll show you a preview before saving anything</span>
          </label>
          <input
            id="file"
            ref={fileInput}
            type="file"
            accept=".csv,.pdf"
            className="hidden"
            disabled={loading}
            onChange={handleFileChange}
          />
        </Card>
      )}

      {loading && !preview && (
        <div className="flex justify-center py-4">
          <Spinner className="h-5 w-5" />
        </div>
      )}

      {preview && (
        <Card>
          <div className="flex items-center justify-between">
            <h3 className="text-sm">Map columns</h3>
            <span className="text-xs text-text-muted">{preview.row_count} rows found</span>
          </div>

          <div className="mt-4 flex flex-col gap-3">
            {STANDARD_FIELDS.map((field) => (
              <div key={field} className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-sm capitalize text-text-secondary">{field}</span>
                <Select
                  value={mapping[field] ?? ''}
                  onChange={(e) => setMapping((m) => ({ ...m, [field]: e.target.value }))}
                >
                  <option value="">Not mapped</option>
                  {preview.raw_headers.map((header) => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </Select>
              </div>
            ))}
          </div>

          {preview.sample_rows.length > 0 && (
            <div className="mt-5">
              <p className="mb-2 text-xs font-medium text-text-muted">Preview</p>
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-surface-3">
                      {preview.raw_headers.map((h) => (
                        <th key={h} className="whitespace-nowrap px-3 py-1.5 font-medium text-text-muted">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample_rows.map((row, i) => (
                      <tr key={i} className="border-t border-border">
                        {preview.raw_headers.map((h) => (
                          <td key={h} className="whitespace-nowrap px-3 py-1.5 text-text-secondary">
                            {String(row[h] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={reset} disabled={loading}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={loading}>
              {loading ? 'Saving…' : `Save ${preview.row_count} rows`}
            </Button>
          </div>
        </Card>
      )}

      {result && (
        <Card>
          <h3 className="text-sm">Import complete</h3>
          <p className="mt-2 text-2xl font-semibold text-text-primary">{result.saved_count} saved</p>
          {result.skipped_count > 0 && (
            <p className="mt-1 text-sm text-status-critical">{result.skipped_count} rows skipped</p>
          )}
          {result.errors.length > 0 && (
            <ul className="mt-3 max-h-40 overflow-y-auto rounded-lg bg-surface-3 p-3 text-xs text-text-muted">
              {result.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
          <Button variant="secondary" className="mt-4" onClick={reset}>
            Upload another file
          </Button>
        </Card>
      )}
    </div>
  )
}
