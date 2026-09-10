import ErrorBanner from './ErrorBanner'
import InputForm from './InputForm'

export default function LandingView({
  websiteUrl,
  githubUrl,
  onWebsiteChange,
  onGithubChange,
  onSubmit,
  loading,
  validationError,
  errorMsg,
}) {
  return (
    <section className="relative flex min-h-[calc(100vh-56px)] items-center justify-center overflow-hidden px-6">
      <div className="dot-grid-bg" aria-hidden="true" />

      <div className="relative z-1 mx-auto w-full max-w-[620px] text-center">
        <div className="mb-6 flex items-center justify-center gap-3 text-text-muted">
          <span aria-hidden="true" className="h-px w-8 bg-border-default" />
          <span className="font-code text-[11px] tracking-[0.1em] text-accent">
            DEVELOPER TOOL
          </span>
          <span aria-hidden="true" className="h-px w-8 bg-border-default" />
        </div>

        <h1 className="mx-auto max-w-[16ch] text-display font-bold leading-[1.05] tracking-[-0.04em] text-text-primary">
          Make your product AI-agent ready.
        </h1>

        <p className="mx-auto mt-6 max-w-[50ch] text-body leading-[1.6] text-text-secondary">
          Paste your website and GitHub repo. We&apos;ll generate{' '}
          <code className="font-code text-[0.85em] text-text-primary">llms.txt</code>, an{' '}
          <code className="font-code text-[0.85em] text-text-primary">MCP server</code>,{' '}
          <code className="font-code text-[0.85em] text-text-primary">OpenAPI spec</code>, and a
          full agent-readiness audit. Takes ~15 seconds.
        </p>

        <div className="mt-10">
          <InputForm
            websiteUrl={websiteUrl}
            githubUrl={githubUrl}
            onWebsiteChange={onWebsiteChange}
            onGithubChange={onGithubChange}
            onSubmit={onSubmit}
            loading={loading}
            validationError={validationError}
          />
          <ErrorBanner message={errorMsg} />
        </div>
      </div>
    </section>
  )
}
