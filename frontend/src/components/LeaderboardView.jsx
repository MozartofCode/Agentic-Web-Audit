import { useEffect, useState } from 'react'
import { getLeaderboard } from '../api'
import { scoreTextClass } from '../status'

const BAR_FILL = { good: 'bg-score-good', warn: 'bg-score-warn', bad: 'bg-score-bad' }

function barClass(score) {
  if (score >= 70) return BAR_FILL.good
  if (score >= 40) return BAR_FILL.warn
  return BAR_FILL.bad
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return iso
  }
}

function StatTile({ value, label }) {
  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-4">
      <p className="font-code text-[1.75rem] font-medium leading-none text-text-primary">{value}</p>
      <p className="mt-2 font-ui text-[13px] text-text-secondary">{label}</p>
    </div>
  )
}

function FilterChip({ label, active, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      className={`h-8 rounded border px-3 font-ui text-[13px] transition-colors duration-100 focus:outline-none focus:ring-2 focus:ring-accent/30 ${
        active
          ? 'border-accent/40 bg-accent-dim text-accent'
          : 'border-border-default text-text-secondary hover:border-border-strong hover:bg-bg-elevated'
      }`}
    >
      {label}
    </button>
  )
}

function LeaderboardRow({ entry, rank, onScan }) {
  const blocked = entry.blocked_answer_bots.length
  return (
    <li className="grid grid-cols-[2rem_minmax(0,1fr)_3rem_auto] items-center gap-3 border-b border-border-subtle px-4 py-3 last:border-b-0 sm:grid-cols-[2.5rem_minmax(0,1fr)_9rem_3rem_auto] sm:gap-4">
      <span className="font-code text-[13px] text-text-muted">{rank}</span>
      <div className="min-w-0">
        <p className="truncate font-code text-[14px] text-text-primary">{entry.domain}</p>
        <p className="truncate font-ui text-[12px] text-text-muted">
          {entry.category}
          {entry.has_llms_txt && <span className="text-score-good"> · llms.txt</span>}
          {blocked > 0 && (
            <span className="text-score-bad">
              {' '}
              · blocks {blocked} AI answer bot{blocked === 1 ? '' : 's'}
            </span>
          )}
        </p>
      </div>
      <span className="hidden h-1.5 w-full rounded bg-border-subtle sm:block" aria-hidden="true">
        <span
          className={`block h-full w-(--score) rounded ${barClass(entry.overall)}`}
          style={{ '--score': `${entry.overall}%` }}
        />
      </span>
      <span className={`text-right font-code text-[15px] font-medium ${scoreTextClass(entry.overall)}`}>
        {entry.overall}
        <span className="ml-1 text-[12px] text-text-muted">{entry.grade}</span>
      </span>
      <button
        type="button"
        onClick={() => onScan(entry.url)}
        aria-label={`Full report for ${entry.domain}`}
        className="h-8 rounded border border-border-default px-2 font-ui text-[12px] text-text-secondary transition-colors duration-100 hover:border-border-strong hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30 sm:px-3 sm:text-[13px]"
      >
        <span className="hidden sm:inline">Full report</span>
        <span className="sm:hidden">Scan</span>
      </button>
    </li>
  )
}

export default function LeaderboardView({ onScan }) {
  const [board, setBoard] = useState(null)
  const [error, setError] = useState('')
  const [category, setCategory] = useState('All')

  useEffect(() => {
    let cancelled = false
    getLeaderboard()
      .then((data) => {
        if (!cancelled) setBoard(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Couldn't load the leaderboard.")
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return (
      <section className="mx-auto max-w-[900px] px-4 pb-24 pt-8 sm:px-6">
        <p role="alert" className="rounded border border-score-bad/30 bg-score-bad-bg p-4 font-ui text-body text-text-primary">
          {error}
        </p>
      </section>
    )
  }

  if (!board) {
    return (
      <section className="mx-auto max-w-[900px] px-4 pb-24 pt-8 sm:px-6" role="status" aria-live="polite">
        <p className="font-ui text-body text-text-secondary">Loading leaderboard…</p>
      </section>
    )
  }

  const ranked = board.entries.map((entry, i) => ({ entry, rank: i + 1 }))
  const shown = category === 'All' ? ranked : ranked.filter(({ entry }) => entry.category === category)

  return (
    <section className="results-enter mx-auto max-w-[900px] px-4 pb-24 pt-8 sm:px-6">
      <h1 className="font-ui text-h1 font-semibold text-text-primary">AI-readiness leaderboard</h1>
      <p className="mt-2 max-w-[640px] font-ui text-body text-text-secondary">
        How well well-known websites can be read and used by AI assistants and agents. Scores come
        from the same measured checks as a full report; no AI is involved in the ranking.
        {board.generated_at && <> Last measured {formatDate(board.generated_at)}.</>}
      </p>

      {board.stats ? (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile value={board.stats.sites} label="Sites scored" />
          <StatTile value={board.stats.median} label="Median score" />
          <StatTile value={`${board.stats.with_llms_txt_pct}%`} label="Publish an llms.txt" />
          <StatTile value={`${board.stats.blocking_answer_bots_pct}%`} label="Block AI answer bots" />
        </div>
      ) : (
        <p className="mt-6 font-ui text-body text-text-secondary">No leaderboard has been published yet.</p>
      )}

      {board.categories.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2" aria-label="Filter by category">
          {['All', ...board.categories].map((c) => (
            <FilterChip key={c} label={c} active={c === category} onSelect={() => setCategory(c)} />
          ))}
        </div>
      )}

      {shown.length > 0 && (
        <ol className="mt-4 rounded border border-border-subtle bg-bg-surface">
          {shown.map(({ entry, rank }) => (
            <LeaderboardRow key={entry.domain} entry={entry} rank={rank} onScan={onScan} />
          ))}
        </ol>
      )}

      {board.failed.length > 0 && (
        <div className="mt-8">
          <h2 className="font-ui text-h2 font-semibold text-text-primary">Couldn&apos;t be scored</h2>
          <p className="mt-1 font-ui text-[13px] text-text-secondary">
            These sites turned our scanner away. Many AI agents get the same answer.
          </p>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {board.failed.map((f) => (
              <li key={f.domain} className="rounded border border-border-subtle bg-bg-surface px-4 py-2.5">
                <p className="font-code text-[13px] text-text-primary">{f.domain}</p>
                <p className="font-ui text-[12px] text-text-muted">{f.error}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
