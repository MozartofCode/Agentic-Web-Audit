export default function Header({ showNewAnalysis, onNewAnalysis }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-100 h-14 border-b border-border-subtle bg-bg-base/85 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-[900px] items-center justify-between px-6">
        {showNewAnalysis ? (
          <button
            type="button"
            onClick={onNewAnalysis}
            className="h-8 rounded border border-border-default bg-transparent px-3 font-ui text-[13px] font-medium text-text-secondary transition-colors duration-100 hover:border-border-strong hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            ← New Analysis
          </button>
        ) : (
          <span />
        )}

        {!showNewAnalysis && (
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hidden font-ui text-[13px] text-text-muted transition-colors duration-100 hover:text-text-secondary sm:inline-block"
          >
            Star on GitHub
          </a>
        )}
      </div>
    </header>
  )
}
