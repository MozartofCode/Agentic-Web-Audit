/** Display metadata for audit check statuses and score colors (tokens from UI.md). */

export const STATUS = {
  fail: { icon: '✗', label: 'Fail', text: 'text-score-bad', border: 'border-l-score-bad' },
  warn: { icon: '!', label: 'Warning', text: 'text-score-warn', border: 'border-l-score-warn' },
  pass: { icon: '✓', label: 'Pass', text: 'text-score-good', border: 'border-l-score-good' },
  na: { icon: '–', label: 'Not applicable', text: 'text-text-muted', border: 'border-l-border-default' },
}

export const STATUS_ORDER = ['fail', 'warn', 'pass', 'na']

export function scoreTextClass(score) {
  if (score === null || score === undefined) return 'text-text-muted'
  if (score >= 70) return 'text-score-good'
  if (score >= 40) return 'text-score-warn'
  return 'text-score-bad'
}

export function scoreStrokeClass(score) {
  if (score === null || score === undefined) return 'stroke-border-default'
  if (score >= 70) return 'stroke-score-good'
  if (score >= 40) return 'stroke-score-warn'
  return 'stroke-score-bad'
}
