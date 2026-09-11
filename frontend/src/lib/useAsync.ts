import { useCallback, useEffect, useState } from 'react'
import { apiErrorMessage } from './api'

export interface AsyncState<T> {
  data: T | null
  /** True until the first result (or error) arrives, and again on reload. */
  loading: boolean
  error: string | null
  reload: () => void
}

/**
 * Run an async fetch and track loading/error alongside the result.
 *
 * The dashboard fetches four independent things, and doing that by hand
 * meant three pieces of state per panel and a `.catch()` that quietly
 * swallowed the reason. This keeps each panel to one line and makes the
 * failure message available to render.
 *
 * `deps` behaves like a useEffect dependency list. A fetch whose deps
 * change while it's still in flight has its result discarded, so a slow
 * response for last month can't overwrite this month's.
 */
export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let active = true

    setLoading(true)
    setError(null)

    fetcher()
      .then((result) => {
        if (active) setData(result)
      })
      .catch((err) => {
        if (active) setError(apiErrorMessage(err))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
    // `fetcher` is recreated every render by design; the caller's deps are
    // what decides when to refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { data, loading, error, reload }
}
