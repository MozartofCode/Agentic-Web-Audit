import ArtifactSection from './ArtifactSection'
import CheckList from './CheckList'
import CrawlerMatrix from './CrawlerMatrix'
import ScoreHero from './ScoreHero'

function domainOf(url) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export default function ResultsView({ results }) {
  const { audit } = results
  const scanned = audit.pages_scanned

  return (
    <section className="results-enter mx-auto max-w-[900px] px-4 pb-24 pt-8 sm:px-6">
      {scanned.length > 0 && (
        <p className="mb-6 font-ui text-[14px] font-medium text-text-muted">
          <span className="text-score-good">✓</span>{' '}
          <span className="text-text-secondary">Analysis complete for</span>{' '}
          <span className="text-text-primary">{domainOf(scanned[0])}</span>
          {' · '}
          {scanned.length} {scanned.length === 1 ? 'page' : 'pages'} read
        </p>
      )}

      <div className="rounded border border-border-subtle bg-bg-surface p-6">
        <h1 className="font-ui text-[18px] font-semibold tracking-[-0.02em] text-text-primary">
          {results.product_name}
        </h1>
        <p className="mt-2 font-ui text-body text-text-secondary">{results.product_summary}</p>
      </div>

      <div className="mt-6">
        <ScoreHero audit={audit} />
      </div>

      {audit.crawler_access.length > 0 && (
        <div className="mt-6">
          <CrawlerMatrix entries={audit.crawler_access} />
        </div>
      )}

      <div className="mt-6">
        <CheckList categories={audit.categories} checks={audit.checks} />
      </div>

      <div className="mt-6">
        <h2 className="mb-3 font-ui text-h2 font-semibold text-text-primary">Fix-it pack</h2>
        <ArtifactSection artifacts={results.artifacts} />
      </div>
    </section>
  )
}
