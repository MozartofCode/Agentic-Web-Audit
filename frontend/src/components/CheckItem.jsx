import { STATUS } from '../status'
import CopyButton from './CopyButton'

export default function CheckItem({ check }) {
  const meta = STATUS[check.status]
  const hasFix = Boolean(check.fix)

  return (
    <details className={`group rounded border border-border-subtle border-l-2 bg-bg-base ${meta.border}`}>
      <summary className="flex cursor-pointer list-none items-start gap-3 px-4 py-3 hover:bg-bg-elevated/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/30">
        <span className={`mt-0.5 w-4 shrink-0 text-center font-code text-[13px] font-medium ${meta.text}`} aria-label={meta.label}>
          {meta.icon}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-ui text-[14px] font-medium text-text-primary">{check.title}</span>
          <span className="mt-0.5 block font-ui text-[13px] text-text-secondary group-open:hidden">
            {check.evidence.length > 140 ? `${check.evidence.slice(0, 140)}…` : check.evidence}
          </span>
        </span>
        <span className="mt-0.5 shrink-0 font-code text-[12px] text-text-muted" aria-hidden="true">
          <span className="group-open:hidden">+</span>
          <span className="hidden group-open:inline">−</span>
        </span>
      </summary>

      <div className="space-y-4 border-t border-border-subtle px-4 pb-4 pt-3 sm:pl-11">
        <div>
          <p className="font-ui text-[12px] font-medium uppercase tracking-wide text-text-muted">What we found</p>
          <p className="mt-1 break-words font-ui text-[13px] text-text-secondary">{check.evidence}</p>
        </div>
        <div>
          <p className="font-ui text-[12px] font-medium uppercase tracking-wide text-text-muted">Why it matters</p>
          <p className="mt-1 font-ui text-[13px] text-text-secondary">{check.why}</p>
        </div>
        {hasFix && (
          <div>
            <div className="flex items-center justify-between gap-2">
              <p className="font-ui text-[12px] font-medium uppercase tracking-wide text-text-muted">How to fix</p>
              <CopyButton text={check.fix} />
            </div>
            <pre className="code-viewer mt-2 max-h-[320px] overflow-auto rounded border border-border-subtle bg-bg-panel p-3 font-code text-[12px] leading-relaxed whitespace-pre-wrap break-words text-text-code">
              {check.fix}
            </pre>
          </div>
        )}
      </div>
    </details>
  )
}
