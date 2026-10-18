import { STATUS } from '../status'
import CopyButton from './CopyButton'

const EFFORT_LABEL = {
  minutes: '5 min',
  hour: '~1 hour',
  dev: 'Developer needed',
}

function FixRow({ fix, rank }) {
  const meta = STATUS[fix.status]

  return (
    <li>
      <details className={`group rounded border border-border-subtle border-l-2 bg-bg-base ${meta.border}`}>
        <summary className="flex cursor-pointer list-none items-start gap-3 px-4 py-3 hover:bg-bg-elevated/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/30">
          <span className="mt-0.5 w-4 shrink-0 text-center font-code text-[13px] text-text-muted">{rank}</span>
          <span className="min-w-0 flex-1">
            <span className="block font-ui text-[14px] font-medium text-text-primary">{fix.title}</span>
            <span className="mt-0.5 block font-ui text-[13px] text-text-secondary group-open:hidden">
              {fix.evidence.length > 120 ? `${fix.evidence.slice(0, 120)}…` : fix.evidence}
            </span>
            <span className="mt-2 flex flex-wrap items-center gap-2">
              <span className="rounded border border-border-default px-2 py-0.5 font-ui text-[11px] text-text-secondary">
                {EFFORT_LABEL[fix.effort]}
              </span>
              <span className={`font-ui text-[11px] ${meta.text}`}>{meta.label}</span>
              <span className="font-ui text-[12px] text-accent">
                <span className="group-open:hidden">Show fix ▾</span>
                <span className="hidden group-open:inline">Hide fix ▴</span>
              </span>
            </span>
          </span>
          <span className="shrink-0 text-right">
            <span className="block font-code text-[15px] font-medium text-score-good">+{fix.points}</span>
            <span className="block font-ui text-[11px] text-text-muted">points</span>
          </span>
        </summary>

        <div className="space-y-3 border-t border-border-subtle px-4 pb-4 pt-3 sm:pl-11">
          <p className="break-words font-ui text-[13px] text-text-secondary">{fix.evidence}</p>
          <div className="flex items-center justify-between gap-2">
            <p className="font-ui text-[12px] font-medium uppercase tracking-wide text-text-muted">How to fix</p>
            <CopyButton text={fix.fix} />
          </div>
          <pre className="code-viewer max-h-[320px] overflow-auto rounded border border-border-subtle bg-bg-panel p-3 font-code text-[12px] leading-relaxed whitespace-pre-wrap break-words text-text-code">
            {fix.fix}
          </pre>
        </div>
      </details>
    </li>
  )
}

export default function TopFixes({ fixes }) {
  if (!fixes.length) return null

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <h2 className="font-ui text-h2 font-semibold text-text-primary">
        Top {fixes.length} {fixes.length === 1 ? 'fix' : 'fixes'}
      </h2>
      <p className="mt-1 font-ui text-small text-text-secondary">
        The most impact for the least effort. Points are the estimated gain if that one check
        passes. Open a fix to see exactly what to change.
      </p>
      <ol className="mt-4 space-y-2">
        {fixes.map((fix, i) => (
          <FixRow key={fix.check_id} fix={fix} rank={i + 1} />
        ))}
      </ol>
    </div>
  )
}
