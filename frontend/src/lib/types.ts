// Mirrors backend/app/schemas/*.py and backend/app/models/*.py.
// Keep in sync by hand — no shared codegen yet.

export type TransactionType = 'spend' | 'earn'
export type TransactionSource = 'manual' | 'csv' | 'pdf'
export type CategorySource = 'rule_based' | 'ml' | 'manual_correction' | 'uncategorized'

export interface User {
  id: number
  email: string
  full_name: string | null
}

export interface Transaction {
  id: number
  date: string
  description: string
  /** Original source text, before cleaning. Null for older rows. */
  raw_description: string | null
  amount: number
  type: TransactionType
  category_id: number | null
  category_name: string | null
  category_source: CategorySource
  source: TransactionSource
}

export interface TransactionCreate {
  date: string
  description: string
  /** Always positive — the backend stores magnitude and uses `type` for direction. */
  amount: number
  type: TransactionType
  category_id: number | null
}

export interface TransactionFilters {
  start_date?: string
  end_date?: string
  category_id?: number
  type?: TransactionType
  search?: string
  page?: number
  page_size?: number
}

export interface Category {
  id: number
  name: string
  description: string | null
}

/**
 * Progress towards a trained ML categorizer, from
 * GET /categorization/training-status and POST /categorization/train.
 */
export interface TrainingResult {
  message: string
  training_examples: number
  categories_covered: number
  is_trained: boolean
  minimum_examples: number | null
}

/**
 * A page of results plus the total row count, which the API returns in
 * the X-Total-Count header rather than wrapping the array.
 */
export interface Paginated<T> {
  items: T[]
  total: number
}

export interface DashboardSummary {
  total_earned: number
  total_spent: number
  balance: number
  month: string
}

export interface CategoryBreakdownItem {
  category_name: string
  total_amount: number
  percentage: number
}

export interface TrendPoint {
  period: string
  total_spent: number
  total_earned: number
}

export interface InsightAlert {
  category_name: string
  message: string
  current_amount: number
  average_amount: number
  severity: 'info' | 'warning'
}

export interface ColumnMappingSuggestion {
  upload_id: string
  raw_headers: string[]
  mapping: Record<string, string | null>
  sample_rows: Record<string, unknown>[]
  row_count: number
}

export interface UploadResult {
  saved_count: number
  skipped_count: number
  errors: string[]
}

export const STANDARD_FIELDS = ['date', 'description', 'amount', 'type'] as const
