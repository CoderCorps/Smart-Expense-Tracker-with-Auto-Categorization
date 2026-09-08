// Fixed categorical hue order — see .claude/CLAUDE.md and the dataviz skill.
// Never assign hue by rank/index-of-current-filter; always by identity (category name).
export const SERIES_HEXES = [
  'var(--series-1)',
  'var(--series-2)',
  'var(--series-3)',
  'var(--series-4)',
  'var(--series-5)',
  'var(--series-6)',
  'var(--series-7)',
  'var(--series-8)',
]

const assigned = new Map<string, string>()
let nextSlot = 0

/** Stable color per category name — first-seen order, capped at 8 slots + "Other". */
export function colorForCategory(name: string): string {
  if (!assigned.has(name)) {
    if (nextSlot < SERIES_HEXES.length) {
      assigned.set(name, SERIES_HEXES[nextSlot])
      nextSlot += 1
    } else {
      assigned.set(name, 'var(--text-muted)')
    }
  }
  return assigned.get(name)!
}
