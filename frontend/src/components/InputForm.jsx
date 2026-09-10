export default function InputForm({
  websiteUrl,
  githubUrl,
  onWebsiteChange,
  onGithubChange,
  onSubmit,
  loading,
  validationError,
}) {
  function handleSubmit(e) {
    e.preventDefault()
    onSubmit()
  }

  const inputBorder = validationError ? 'border-score-bad' : 'border-border-default'

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[520px]">
      <div className="flex flex-col gap-3">
        <label className="relative block">
          <span className="sr-only">Website URL</span>
          <span
            aria-hidden="true"
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-text-muted"
          >
            🌐
          </span>
          <input
            type="url"
            value={websiteUrl}
            onChange={(e) => onWebsiteChange(e.target.value)}
            placeholder="https://yoursite.com"
            className={`h-12 w-full rounded border ${inputBorder} bg-bg-elevated pl-10 pr-4 font-code text-[14px] text-text-secondary placeholder:text-text-muted transition-all duration-150 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20`}
          />
        </label>

        <label className="relative block">
          <span className="sr-only">GitHub repository URL</span>
          <span
            aria-hidden="true"
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-text-muted"
          >
            ⌥
          </span>
          <input
            type="url"
            value={githubUrl}
            onChange={(e) => onGithubChange(e.target.value)}
            placeholder="https://github.com/org/repo"
            className={`h-12 w-full rounded border ${inputBorder} bg-bg-elevated pl-10 pr-4 font-code text-[14px] text-text-secondary placeholder:text-text-muted transition-all duration-150 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20`}
          />
        </label>
      </div>

      {validationError && (
        <p role="alert" className="fade-in mt-2 text-[13px] text-score-bad">
          {validationError}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="group mt-6 h-12 w-full rounded bg-accent font-ui text-[15px] font-semibold tracking-[-0.01em] text-bg-base transition-all duration-100 hover:brightness-108 active:brightness-92 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-accent/30"
      >
        Analyze my product{' '}
        <span className="inline-block transition-transform duration-100 group-hover:translate-x-1">
          →
        </span>
      </button>

      <p className="mt-3 text-center font-ui text-[13px] text-text-muted">
        At least one URL required · Public repos only
      </p>
    </form>
  )
}
