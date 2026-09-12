import ArtifactSection from './ArtifactSection'
import AuditScoreCard from './AuditScoreCard'

export default function ResultsView({ results }) {
  return (
    <section className="results-enter mx-auto max-w-[900px] px-6 pb-24 pt-8">
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
