import AIPreviewCard from './AIPreviewCard'
import ArtifactSection from './ArtifactSection'
import CheckList from './CheckList'
import CrawlerMatrix from './CrawlerMatrix'
import ReportStatus from './ReportStatus'
import ScoreHero from './ScoreHero'
import ShareBar from './ShareBar'
import TopFixes from './TopFixes'

function domainOf(url) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export default function ResultsView({ results, onRescan, onCompare, onOpenReport }) {
  const { audit, fix_pack: fixPack } = results
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

      <ShareBar results={results} onRescan={onRescan} onCompare={onCompare} />

      {(results.delta || results.cached) && (
        <div className="mt-3">
          <ReportStatus results={results} onOpenReport={onOpenReport} />
        </div>
      )}

      <div className="mt-6 rounded border border-border-subtle bg-bg-surface p-6">
        <h1 className="font-ui text-[18px] font-semibold tracking-[-0.02em] text-text-primary">
          {results.product_name}
        </h1>
        <p className="mt-2 font-ui text-body text-text-secondary">{results.product_summary}</p>
      </div>

      <div className="mt-6">
        <ScoreHero audit={audit} />
      </div>

      {audit.top_fixes.length > 0 && (
        <div className="mt-6">
          <TopFixes fixes={audit.top_fixes} />
        </div>
      )}

      <div className="mt-6">
        <AIPreviewCard preview={results.ai_preview} />
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
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-ui text-h2 font-semibold text-text-primary">Fix-it pack</h2>
          {fixPack.platform && (
            <span className="font-ui text-[13px] text-text-muted" title={fixPack.platform.evidence}>
              Built on <span className="text-text-secondary">{fixPack.platform.name}</span>
            </span>
          )}
        </div>
        <ArtifactSection files={fixPack.files} platform={fixPack.platform} />
      </div>
    </section>
  )
}
