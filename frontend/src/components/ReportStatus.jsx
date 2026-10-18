import { reportPath } from '../routes'

function timeAgo(iso) {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 90) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 36) return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`
  const days = Math.round(hours / 24)
  return `${days} days ago`
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

/** Re-scan delta against the previous report for this domain, plus "saved scan" notice. */
export default function ReportStatus({ results, onOpenReport }) {
  const { delta, cached, created_at: createdAt } = results
  if (!delta && !(cached && createdAt)) return null

  const pointsClass =
    delta && delta.points > 0 ? 'text-score-good' : delta && delta.points < 0 ? 'text-score-bad' : 'text-text-secondary'
  const pointsText =
    delta && (delta.points === 0 ? 'No score change' : `${delta.points > 0 ? '+' : ''}${delta.points} points`)

  function handleOpenPrevious(e) {
    e.preventDefault()
    onOpenReport(delta.previous_report_id)
  }

  return (
    <div className="rounded border border-border-subtle bg-bg-surface px-4 py-3">
      {delta && (
        <p className="font-ui text-[14px] text-text-secondary">
          <span className={`font-code font-medium ${pointsClass}`}>{pointsText}</span>
          {delta.now_passing.length > 0 && (
            <>
              {', '}
              <span className="text-text-primary">{plural(delta.now_passing.length, 'check')} now passing</span>
            </>
          )}
          {delta.regressed.length > 0 && (
            <>
              {', '}
              <span className="text-score-bad">{plural(delta.regressed.length, 'check')} slipped</span>
            </>
          )}{' '}
          since the{' '}
          <a
            href={reportPath(delta.previous_report_id)}
            onClick={handleOpenPrevious}
            className="text-accent underline-offset-2 hover:underline"
          >
            previous scan
          </a>{' '}
          ({delta.previous_overall}/100, {timeAgo(delta.previous_created_at)}).
        </p>
      )}
      {delta && delta.now_passing.length > 0 && (
        <p className="mt-1 font-ui text-[13px] text-text-muted">
          Now passing: {delta.now_passing.join(', ')}
        </p>
      )}
      {cached && createdAt && (
        <p className={`font-ui text-[13px] text-text-muted ${delta ? 'mt-1' : ''}`}>
          Saved scan from {timeAgo(createdAt)}. Use Re-scan to check your live site again.
        </p>
      )}
    </div>
  )
}
