import { comparePath, reportPath, siteDomain } from '../routes'
import { STATUS, scoreTextClass } from '../status'
import CopyButton from './CopyButton'

const MAX_DIFFERENCES = 12
const ROW = 'grid grid-cols-[minmax(0,1fr)_3.5rem_3.5rem] items-center gap-2 sm:grid-cols-[minmax(0,1fr)_7rem_7rem] sm:gap-4'
const BAR_FILL = { good: 'bg-score-good', warn: 'bg-score-warn', bad: 'bg-score-bad' }

function barClass(score) {
  if (score >= 70) return BAR_FILL.good
  if (score >= 40) return BAR_FILL.warn
  return BAR_FILL.bad
}

function SiteCard({ report, lead, onOpenReport }) {
  const { overall, grade } = report.audit
  const domain = siteDomain(report.website_url) || report.product_name

  function handleOpen(e) {
    e.preventDefault()
    onOpenReport(report.report_id)
  }

  return (
    <div
      className={`min-w-0 rounded border bg-bg-surface p-4 sm:p-6 ${lead > 0 ? 'border-accent/40' : 'border-border-subtle'}`}
    >
      <p className="truncate font-code text-[13px] text-text-secondary sm:text-[14px]" title={domain}>
        {domain}
      </p>
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <span className={`font-code text-[2.5rem] font-medium leading-none sm:text-[4rem] ${scoreTextClass(overall)}`}>
          {overall}
        </span>
        <span
          className={`mb-1 rounded border border-border-default px-2 py-0.5 font-code text-[14px] font-medium sm:text-[18px] ${scoreTextClass(overall)}`}
        >
          {grade}
        </span>
      </div>
      <p className="mt-2 font-ui text-[12px] text-text-muted sm:text-[13px]">
        {lead > 0 ? <span className="text-accent">Leads by {lead}</span> : lead === 0 ? 'Tied' : ' '}
      </p>
      {report.report_id && (
        <a
          href={reportPath(report.report_id)}
          onClick={handleOpen}
          className="mt-3 inline-block font-ui text-[13px] text-accent underline-offset-2 hover:underline"
        >
          Full report →
        </a>
      )}
    </div>
  )
}

function ScoreCell({ score, leads }) {
  if (score === null || score === undefined) {
    return <span className="text-right font-code text-[13px] text-text-muted">n/a</span>
  }
  return (
    <span className="block">
      <span
        className={`block text-right font-code text-[14px] ${leads ? 'font-semibold' : ''} ${scoreTextClass(score)}`}
      >
        {score}
      </span>
      <span className="mt-1 block h-1 w-full rounded-full bg-border-subtle">
        <span className={`block h-full rounded-full ${barClass(score)}`} style={{ width: `${score}%` }} />
      </span>
    </span>
  )
}

function differingChecks(a, b) {
  const other = new Map(b.audit.checks.map((c) => [c.id, c]))
  return a.audit.checks
    .map((check) => [check, other.get(check.id)])
    .filter(([x, y]) => y && x.status !== 'na' && y.status !== 'na' && x.status !== y.status)
    .sort(([x], [y]) => y.weight - x.weight)
    .slice(0, MAX_DIFFERENCES)
}

export default function CompareView({ reports, onOpenReport }) {
  const [a, b] = reports
  const domains = reports.map((r) => siteDomain(r.website_url) || r.product_name)
  const diff = a.audit.overall - b.audit.overall
  const categoriesB = new Map(b.audit.categories.map((c) => [c.id, c]))
  const differences = differingChecks(a, b)
  const permalink =
    a.report_id && b.report_id ? `${window.location.origin}${comparePath(a.report_id, b.report_id)}` : ''

  return (
    <section className="results-enter mx-auto max-w-[900px] px-4 pb-24 pt-8 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="font-ui text-[18px] font-semibold tracking-[-0.02em] text-text-primary">
          Side by side
        </h1>
        {permalink && <CopyButton text={permalink} label="Copy link" />}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <SiteCard report={a} lead={diff} onOpenReport={onOpenReport} />
        <SiteCard report={b} lead={-diff} onOpenReport={onOpenReport} />
      </div>

      <div className="mt-6 rounded border border-border-subtle bg-bg-surface p-4 sm:p-6">
        <h2 className="font-ui text-h2 font-semibold text-text-primary">By category</h2>
        <div className={`${ROW} mt-4 border-b border-border-subtle pb-2`}>
          <span />
          {domains.map((d) => (
            <span key={d} className="truncate text-right font-code text-[11px] text-text-muted" title={d}>
              {d}
            </span>
          ))}
        </div>
        <ul className="divide-y divide-border-subtle">
          {a.audit.categories.map((cat) => {
            const scoreA = cat.score
            const scoreB = categoriesB.get(cat.id)?.score ?? null
            const both = scoreA !== null && scoreB !== null
            return (
              <li key={cat.id} className={`${ROW} py-3`}>
                <span className="min-w-0 font-ui text-[13px] text-text-secondary sm:text-[14px]">{cat.label}</span>
                <ScoreCell score={scoreA} leads={both && scoreA > scoreB} />
                <ScoreCell score={scoreB} leads={both && scoreB > scoreA} />
              </li>
            )
          })}
        </ul>
      </div>

      <div className="mt-6 rounded border border-border-subtle bg-bg-surface p-4 sm:p-6">
        <h2 className="font-ui text-h2 font-semibold text-text-primary">Where they differ</h2>
        {differences.length === 0 ? (
          <p className="mt-2 font-ui text-small text-text-secondary">
            Both sites got the same result on every check that applies to both.
          </p>
        ) : (
          <>
            <p className="mt-1 font-ui text-small text-text-secondary">
              Checks one site passes and the other doesn't, most important first.
            </p>
            <div className={`${ROW} mt-4 border-b border-border-subtle pb-2`}>
              <span />
              {domains.map((d) => (
                <span key={d} className="truncate text-center font-code text-[11px] text-text-muted" title={d}>
                  {d}
                </span>
              ))}
            </div>
            <ul className="divide-y divide-border-subtle">
              {differences.map(([x, y]) => (
                <li key={x.id} className={`${ROW} py-2.5`}>
                  <span className="min-w-0 font-ui text-[13px] text-text-primary">{x.title}</span>
                  {[x, y].map((c, i) => (
                    <span
                      key={i}
                      className={`text-center font-code text-[14px] ${STATUS[c.status].text}`}
                      title={STATUS[c.status].label}
                    >
                      {STATUS[c.status].icon}
                      <span className="sr-only"> {STATUS[c.status].label}</span>
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
