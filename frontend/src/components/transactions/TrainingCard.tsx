import { useState } from 'react'
import { apiErrorMessage } from '../../lib/api'
import { categorizationApi } from '../../lib/resources'
import { useAsync } from '../../lib/useAsync'
import type { TrainingResult } from '../../lib/types'
import { Button, Card, Skeleton } from '../ui'

/**
 * Progress towards a personalised categorizer.
 *
 * Every category the user corrects below becomes a labeled training
 * example, so this card exists to make that loop visible — otherwise the
 * ML feature is invisible until someone finds the endpoint.
 */
export function TrainingCard({ correctionCount }: { correctionCount: number }) {
  const status = useAsync<TrainingResult>(
    () => categorizationApi.trainingStatus(),
    [correctionCount],
  )

  const [training, setTraining] = useState(false)
  const [result, setResult] = useState<TrainingResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleTrain() {
    setTraining(true)
    setError(null)
    try {
      setResult(await categorizationApi.train())
      status.reload()
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not train the model.'))
    } finally {
      setTraining(false)
    }
  }

  if (status.loading) {
    return (
      <Card>
        <Skeleton className="h-4 w-48" />
        <Skeleton className="mt-3 h-2 w-full" />
      </Card>
    )
  }

  // A failure here is not worth a banner — the page's real job is the
  // transaction table, and this panel is supplementary.
  if (status.error || !status.data) return null

  const { training_examples, minimum_examples, is_trained } = status.data
  const target = minimum_examples ?? training_examples
  const ready = training_examples >= target
  const progress = target > 0 ? Math.min(100, (training_examples / target) * 100) : 100

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm">Smart categorization</h3>
          <p className="mt-0.5 text-xs text-text-muted">
            {result?.message ?? error ?? status.data.message}
          </p>
        </div>

        {ready && (
          <Button variant="secondary" onClick={handleTrain} disabled={training}>
            {training ? 'Training…' : is_trained ? 'Retrain model' : 'Train model'}
          </Button>
        )}
      </div>

      {!is_trained && (
        <div className="mt-3">
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3"
            role="progressbar"
            aria-valuenow={training_examples}
            aria-valuemin={0}
            aria-valuemax={target}
            aria-label="Corrections collected"
          >
            <div
              className="h-full rounded-full bg-series-1 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1.5 text-xs tabular-nums text-text-muted">
            {training_examples} of {target} corrections
          </p>
        </div>
      )}
    </Card>
  )
}
