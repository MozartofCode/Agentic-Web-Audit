import ErrorBanner from './ErrorBanner'
import InputForm from './InputForm'

export default function LandingView({
  inputMode,
  onModeChange,
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
        <h1 className="mx-auto max-w-[16ch] text-display font-bold leading-[1.05] tracking-[-0.04em] text-text-primary">
          Make your product agent ready.
        </h1>

        <p className="mx-auto mt-6 max-w-[50ch] text-body leading-[1.6] text-text-secondary">
          Drop in a website or GitHub repo and we&apos;ll check how ready it is for agents — then
          generate the files it&apos;s missing, like{' '}
          <code className="font-code text-[0.85em] text-text-primary">llms.txt</code>, an{' '}
          <code className="font-code text-[0.85em] text-text-primary">MCP server</code>, and an{' '}
          <code className="font-code text-[0.85em] text-text-primary">OpenAPI spec</code>.
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
        </div>
      </div>
    </section>
  )
}
