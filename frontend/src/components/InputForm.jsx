const MODES = [
  { key: 'website', label: 'Website', icon: '🌐', placeholder: 'https://yoursite.com' },
  { key: 'github', label: 'GitHub Repo', icon: '⌥', placeholder: 'https://github.com/org/repo' },
]

export default function InputForm({
  inputMode,
  onModeChange,
  websiteUrl,
  githubUrl,
  onWebsiteChange,
  onGithubChange,
  onSubmit,
  loading,
  validationError,
}) {
  const activeMode = MODES.find((m) => m.key === inputMode) || MODES[0]
  const value = activeMode.key === 'website' ? websiteUrl : githubUrl
  const onChange = activeMode.key === 'website' ? onWebsiteChange : onGithubChange

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit()
  }

  function handleModeChange(key) {
    onModeChange(key)
    onWebsiteChange('')
    onGithubChange('')
  }

  const inputBorder = validationError ? 'border-score-bad' : 'border-border-default'

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[520px]">
      <div
        role="tablist"
        aria-label="Analyze by"
        className="mx-auto mb-3 inline-flex rounded border border-border-default bg-bg-elevated p-1"
      >
        {MODES.map((mode) => {
          const isActive = mode.key === activeMode.key
          return (
            <button
              key={mode.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => handleModeChange(mode.key)}
              className={`rounded px-4 py-1.5 font-ui text-[13px] font-medium transition-colors duration-100 ${
                isActive
                  ? 'bg-bg-surface text-text-primary'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {mode.label}
            </button>
          )
        })}
      </div>

      <label className="relative block">
        <span className="sr-only">{activeMode.label} URL</span>
        <span
          aria-hidden="true"
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-text-muted"
        >
          {activeMode.icon}
        </span>
        <input
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={activeMode.placeholder}
          className={`h-12 w-full rounded border ${inputBorder} bg-bg-elevated pl-10 pr-4 font-code text-[14px] text-text-secondary placeholder:text-text-muted transition-all duration-150 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20`}
        />
      </label>

      {validationError && (
        <p role="alert" className="fade-in mt-2 text-[13px] text-score-bad">
          {validationError}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="group mt-6 flex h-12 w-full items-center justify-center gap-2 rounded bg-accent font-ui text-[15px] font-semibold tracking-[-0.01em] text-bg-base transition-all duration-100 hover:brightness-108 active:brightness-92 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-accent/30"
      >
        <span>Analyze my product</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="none"
          className="h-4 w-4 shrink-0 transition-transform duration-150 group-hover:translate-x-0.5"
        >
          <path
            d="M4 10h12M12 5l5 5-5 5"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </form>
  )
}
