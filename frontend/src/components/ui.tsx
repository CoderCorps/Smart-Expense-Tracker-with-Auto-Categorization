import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border border-border bg-surface-1 p-5 shadow-sm ${className}`}
    >
      {children}
    </div>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const variants: Record<string, string> = {
    primary: 'bg-series-1 text-white hover:brightness-110',
    secondary: 'bg-surface-3 text-text-primary hover:bg-border',
    ghost: 'text-text-secondary hover:bg-surface-3',
    danger: 'bg-status-critical text-white hover:brightness-110',
  }
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-muted focus:border-series-1 ${props.className ?? ''}`}
    />
  )
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-text-primary outline-none focus:border-series-1 ${props.className ?? ''}`}
    />
  )
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-xs font-medium text-text-muted">{children}</label>
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <div
      className={`h-4 w-4 animate-spin rounded-full border-2 border-border-strong border-t-series-1 ${className}`}
    />
  )
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-status-critical/30 bg-status-critical/10 px-3.5 py-2.5 text-sm text-status-critical">
      <span aria-hidden>⚠</span>
      <span>{message}</span>
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-border py-12 text-center">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      {hint && <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  )
}

/**
 * Placeholder block shown while a panel's data is loading.
 *
 * Sized to roughly match what replaces it, so the layout doesn't jump
 * when the real content arrives.
 */
export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`animate-pulse rounded-md bg-surface-3 ${className}`}
    />
  )
}

/**
 * A panel that failed to load, with a way to try again. Distinct from
 * EmptyState: "nothing here" and "we couldn't fetch it" are different
 * things and shouldn't look alike.
 */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-10 text-center">
      <p className="text-sm font-medium text-text-primary">Couldn't load this</p>
      <p className="max-w-xs text-xs text-text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-1" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Badge({ children, tone = 'default' }: { children: ReactNode; tone?: 'default' | 'good' | 'warning' }) {
  const tones: Record<string, string> = {
    default: 'bg-surface-3 text-text-secondary',
    good: 'bg-status-good/15 text-status-good',
    warning: 'bg-status-warning/20 text-[#8a5a00] dark:text-status-warning',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}
