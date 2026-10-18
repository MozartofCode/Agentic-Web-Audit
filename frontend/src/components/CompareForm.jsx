import ErrorBanner from './ErrorBanner'

const FIELDS = [
  { label: 'Your site', placeholder: 'https://yoursite.com' },
  { label: 'Compare with', placeholder: 'https://competitor.com' },
]

export default function CompareForm({ urls, onUrlsChange, onSubmit, validationError, errorMsg }) {
  function handleSubmit(e) {
    e.preventDefault()
    onSubmit()
  }

  function handleChange(index, value) {
    onUrlsChange(urls.map((u, i) => (i === index ? value : u)))
  }

  const inputBorder = validationError ? 'border-score-bad' : 'border-border-default'

  return (
    <section className="relative flex min-h-[calc(100vh-56px)] items-center justify-center overflow-hidden px-6">
      <div className="dot-grid-bg" aria-hidden="true" />

      <div className="relative z-1 mx-auto w-full max-w-[620px] text-center">
        <h1 className="mx-auto max-w-[18ch] text-h1 font-bold text-text-primary sm:text-display">
          Who do AI assistants understand better?
        </h1>
        <p className="mx-auto mt-6 max-w-[50ch] text-body text-text-secondary">
          Scan two sites side by side: same checks, same AI read, category by category.
        </p>

        <form onSubmit={handleSubmit} className="mx-auto mt-10 w-full max-w-[520px] space-y-3 text-left">
          {FIELDS.map((field, i) => (
            <label key={field.label} className="block">
              <span className="mb-1.5 block font-ui text-[13px] font-medium text-text-secondary">
                {field.label}
              </span>
              <input
                type="url"
                value={urls[i]}
                onChange={(e) => handleChange(i, e.target.value)}
                placeholder={field.placeholder}
                className={`h-12 w-full rounded border ${inputBorder} bg-bg-elevated px-4 font-code text-[14px] text-text-secondary placeholder:text-text-muted transition-all duration-150 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20`}
              />
            </label>
          ))}

          {validationError && (
            <p role="alert" className="fade-in text-[13px] text-score-bad">
              {validationError}
            </p>
          )}

          <button
            type="submit"
            className="mt-3 flex h-12 w-full items-center justify-center rounded bg-accent font-ui text-[15px] font-semibold tracking-[-0.01em] text-bg-base transition-all duration-100 hover:brightness-108 active:brightness-92 focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            Compare
          </button>
          <p className="text-center font-ui text-[12px] text-text-muted">Counts as two scans.</p>
        </form>
        <ErrorBanner message={errorMsg} />
      </div>
    </section>
  )
}
