import ArtifactSection from './ArtifactSection'
import AuditScoreCard from './AuditScoreCard'

function domainOf(url) {
  if (!url) return null
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export default function ResultsView({ results, websiteUrl, githubUrl, elapsedSeconds }) {
  const domains = [domainOf(websiteUrl), domainOf(githubUrl)].filter(Boolean)
  const primaryDomain = domains[0] || results.product_name

  return (
    <section className="results-enter mx-auto max-w-[900px] px-6 pb-24 pt-24">
      <p className="mb-6 font-ui text-[14px] font-medium text-text-muted">
        <span className="text-score-good" aria-hidden="true">
          ✓
        </span>{' '}
        Analysis complete for <span className="text-text-primary">{primaryDomain}</span>
        {elapsedSeconds != null && <> · ~{elapsedSeconds} seconds</>}
      </p>

      <div className="rounded border border-border-subtle bg-bg-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="font-ui text-[18px] font-semibold tracking-[-0.02em] text-text-primary">
            {results.product_name}
          </h1>
        </div>
        <p className="mt-2 font-ui text-body text-text-secondary">{results.product_summary}</p>
      </div>

      <div className="mt-6">
        <AuditScoreCard auditScore={results.audit_score} />
      </div>

      <div className="mt-6">
        <ArtifactSection artifacts={results.artifacts} />
      </div>
    </section>
  )
}
