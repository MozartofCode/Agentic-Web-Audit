import { useState } from 'react'
import { badgeUrl } from '../api'
import { reportPath, siteDomain } from '../routes'
import CopyButton from './CopyButton'

const BUTTON =
  'h-8 shrink-0 rounded border border-border-default bg-transparent px-3 font-ui text-[13px] font-medium text-text-secondary transition-colors duration-100 hover:border-border-strong hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30'

function EmbedSnippet({ label, code }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <p className="font-ui text-[12px] font-medium uppercase tracking-wide text-text-muted">{label}</p>
        <CopyButton text={code} />
      </div>
      <pre className="code-viewer overflow-x-auto rounded border border-border-subtle bg-bg-panel p-3 font-code text-[12px] leading-relaxed whitespace-pre-wrap break-all text-text-code">
        {code}
      </pre>
    </div>
  )
}

export default function ShareBar({ results, onRescan, onCompare }) {
  const [showBadge, setShowBadge] = useState(false)
  const reportId = results.report_id
  const domain = siteDomain(results.website_url)
  const permalink = reportId ? `${window.location.origin}${reportPath(reportId)}` : ''
  const badge = domain ? badgeUrl(domain) : ''
  const canBadge = Boolean(reportId && domain)

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        {reportId && <CopyButton text={permalink} label="Copy link" />}
        {canBadge && (
          <button
            type="button"
            aria-expanded={showBadge}
            onClick={() => setShowBadge((open) => !open)}
            className={BUTTON}
          >
            {showBadge ? 'Hide badge' : 'Get badge'}
          </button>
        )}
        <button type="button" onClick={onRescan} className={BUTTON}>
          ↻ Re-scan
        </button>
        {results.website_url && (
          <button type="button" onClick={onCompare} className={BUTTON}>
            Compare
          </button>
        )}
        {reportId && (
          <span className="ml-auto hidden truncate font-code text-[12px] text-text-muted sm:inline">
            {permalink.replace(/^https?:\/\//, '')}
          </span>
        )}
      </div>

      {canBadge && showBadge && (
        <div className="fade-in mt-4 space-y-3 border-t border-border-subtle pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <img src={badge} alt={`AI-Ready score for ${domain}`} className="h-5" />
            <p className="font-ui text-small text-text-secondary">
              Always shows your latest score. Re-scan after a fix and it updates.
            </p>
          </div>
          <EmbedSnippet label="Markdown" code={`[![AI-Ready score](${badge})](${permalink})`} />
          <EmbedSnippet
            label="HTML"
            code={`<a href="${permalink}"><img src="${badge}" alt="AI-Ready score for ${domain}"></a>`}
          />
        </div>
      )}
    </div>
  )
}
