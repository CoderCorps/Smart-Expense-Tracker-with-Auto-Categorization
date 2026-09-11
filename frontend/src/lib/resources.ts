import { api } from './api'
import type {
  Category,
  CategoryBreakdownItem,
  ColumnMappingSuggestion,
  DashboardSummary,
  InsightAlert,
  Paginated,
  Transaction,
  TransactionCreate,
  TransactionFilters,
  TrainingResult,
  TrendPoint,
  UploadResult,
  User,
} from './types'

export const authApi = {
  async signup(email: string, password: string, fullName: string) {
    const { data } = await api.post<User>('/auth/signup', {
      email,
      password,
      full_name: fullName || null,
    })
    return data
  },

  async login(email: string, password: string) {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    const { data } = await api.post<{ access_token: string; token_type: string }>(
      '/auth/login',
      form,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    )
    return data
  },

  async me() {
    const { data } = await api.get<User>('/auth/me')
    return data
  },
}

export const transactionsApi = {
  async list(filters: TransactionFilters): Promise<Paginated<Transaction>> {
    const response = await api.get<Transaction[]>('/transactions', { params: filters })
    // The total ignores pagination and comes back as a header, so the
    // endpoint can keep returning a plain array. See list_transactions.
    const total = Number(response.headers['x-total-count'] ?? response.data.length)
    return { items: response.data, total }
  },

  async create(payload: TransactionCreate) {
    const { data } = await api.post<Transaction>('/transactions', payload)
    return data
  },

  async updateCategory(id: number, categoryId: number) {
    const { data } = await api.put<Transaction>(`/transactions/${id}/category`, {
      category_id: categoryId,
    })
    return data
  },

  async remove(id: number) {
    await api.delete(`/transactions/${id}`)
  },
}

export const categoriesApi = {
  async list() {
    const { data } = await api.get<Category[]>('/categorization/categories')
    return data
  },
}

export const categorizationApi = {
  async trainingStatus() {
    const { data } = await api.get<TrainingResult>('/categorization/training-status')
    return data
  },

  async train() {
    const { data } = await api.post<TrainingResult>('/categorization/train')
    return data
  },

  async recategorize(transactionId: number) {
    const { data } = await api.post<{ transaction_id: number; category_name: string }>(
      `/categorization/recategorize/${transactionId}`,
    )
    return data
  },
}

export const dashboardApi = {
  async summary(month: string) {
    const { data } = await api.get<DashboardSummary>('/dashboard/summary', { params: { month } })
    return data
  },

  async categoryBreakdown(month?: string) {
    const { data } = await api.get<CategoryBreakdownItem[]>('/dashboard/category-breakdown', {
      params: month ? { month } : undefined,
    })
    return data
  },

  async trends(granularity: 'monthly' | 'daily' = 'monthly') {
    const { data } = await api.get<TrendPoint[]>('/dashboard/trends', { params: { granularity } })
    return data
  },

  async insights() {
    const { data } = await api.get<InsightAlert[]>('/dashboard/insights')
    return data
  },
}

export const uploadApi = {
  async preview(file: File) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<ColumnMappingSuggestion>('/upload/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async confirm(uploadId: string, mapping: Record<string, string>) {
    const { data } = await api.post<UploadResult>('/upload/confirm', {
      upload_id: uploadId,
      mapping,
    })
    return data
  },
}
