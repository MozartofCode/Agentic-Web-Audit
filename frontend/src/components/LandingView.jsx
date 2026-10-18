import ErrorBanner from './ErrorBanner'
import InputForm from './InputForm'

const EXAMPLES = ['python.org', 'stripe.com', 'wikipedia.org']

export default function LandingView({
  inputMode,
  onModeChange,
  websiteUrl,
  githubUrl,
  onWebsiteChange,
  onGithubChange,
  onSubmit,
  onCompare,
  onLeaderboard,
  onExample,
  loading,
  validationError,
  errorMsg,
}) {
  return (
    <section className="relative flex min-h-[calc(100vh-56px)] items-center justify-center overflow-hidden px-6">
      <div className="dot-grid-bg" aria-hidden="true" />

      <div className="relative z-1 mx-auto w-full max-w-[620px] text-center">
        <h1 className="mx-auto max-w-[16ch] text-display font-bold leading-[1.05] tracking-[-0.04em] text-text-primary">
          See your site the way AI sees it.
        </h1>

        <p className="mx-auto mt-6 max-w-[52ch] text-body leading-[1.6] text-text-secondary">
          Find out if ChatGPT, Claude and Perplexity can read your website and answer questions
          about it. You get a score, the evidence behind it, and fixes you can copy and paste.
          Free, no sign-up.
        </p>

        <div className="mt-10">
          <InputForm
            inputMode={inputMode}
            onModeChange={onModeChange}
            websiteUrl={websiteUrl}
            githubUrl={githubUrl}
            onWebsiteChange={onWebsiteChange}
            onGithubChange={onGithubChange}
            onSubmit={onSubmit}
            loading={loading}
            validationError={validationError}
          />
          <ErrorBanner message={errorMsg} />
          <p className="mt-4 font-ui text-[13px] text-text-muted">
            Try:{' '}
            {EXAMPLES.map((example, i) => (
              <span key={example}>
                {i > 0 && ' · '}
                <button
                  type="button"
                  onClick={() => onExample(`https://${example}`)}
                  className="rounded font-code text-text-secondary underline-offset-2 transition-colors duration-100 hover:text-accent hover:underline focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  {example}
                </button>
              </span>
            ))}
          </p>
          <button
            type="button"
            onClick={onCompare}
            className="mt-4 rounded px-2 py-1 font-ui text-[13px] text-text-muted transition-colors duration-100 hover:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            Or compare two sites side by side →
          </button>
          <button
            type="button"
            onClick={onLeaderboard}
            className="mt-1 rounded px-2 py-1 font-ui text-[13px] text-text-muted transition-colors duration-100 hover:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            See how popular sites score →
          </button>
        </div>
      </div>
    </section>
  )
}
