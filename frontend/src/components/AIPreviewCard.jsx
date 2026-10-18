function pathOf(url) {
  try {
    const { pathname } = new URL(url)
    return pathname === '/' ? 'homepage' : pathname
  } catch {
    return url
  }
}

function QuestionRow({ question }) {
  const { answered } = question

  return (
    <li className="flex gap-3 border-b border-border-subtle py-3 last:border-b-0">
      <span
        className={`mt-0.5 w-4 shrink-0 text-center font-code text-[13px] font-medium ${answered ? 'text-score-good' : 'text-score-bad'}`}
        aria-label={answered ? 'Answered on your site' : 'Not answered on your site'}
      >
        {answered ? '✓' : '✗'}
      </span>
      <div className="min-w-0">
        <p className="font-ui text-[14px] text-text-primary">{question.question}</p>
        {answered ? (
          <p className="mt-0.5 font-ui text-[13px] text-text-secondary">
            {question.answer}
            {question.source && (
              <>
                {' '}
                <a
                  href={question.source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-words font-code text-[12px] text-text-muted underline decoration-border-strong underline-offset-2 hover:text-text-secondary"
                >
                  {pathOf(question.source)}
                </a>
              </>
            )}
          </p>
        ) : (
          <p className="mt-0.5 font-ui text-[13px] text-text-muted">
            Not answered on the pages we read — AI will guess or skip you.
          </p>
        )}
      </div>
    </li>
  )
}

export default function AIPreviewCard({ preview }) {
  const { summary, unknowns, questions } = preview
  if (!summary && !questions.length) return null

  const answered = questions.filter((q) => q.answered).length

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <h2 className="font-ui text-h2 font-semibold text-text-primary">How AI sees you</h2>
      <p className="mt-1 font-ui text-small text-text-secondary">
        What an assistant like ChatGPT, Claude or Perplexity would likely say, based only on the
        pages we read. AI-written — a preview, not part of your score.
      </p>

      {summary && (
        <blockquote className="mt-5 border-l-2 border-accent pl-4 font-ui text-body text-text-primary">
          {summary}
        </blockquote>
      )}

      <div className="mt-6 grid gap-6 md:grid-cols-5">
        {questions.length > 0 && (
          <section className={unknowns.length ? 'md:col-span-3' : 'md:col-span-5'}>
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-ui text-[13px] font-medium text-text-primary">
                Questions customers ask AI
              </h3>
              <span className="shrink-0 font-code text-[12px] text-text-muted">
                {answered}/{questions.length} answered
              </span>
            </div>
            <ul className="mt-1">
              {questions.map((q) => (
                <QuestionRow key={q.question} question={q} />
              ))}
            </ul>
          </section>
        )}

        {unknowns.length > 0 && (
          <section className={questions.length ? 'md:col-span-2' : 'md:col-span-5'}>
            <h3 className="font-ui text-[13px] font-medium text-text-primary">
              What AI couldn&apos;t find out
            </h3>
            <ul className="mt-1">
              {unknowns.map((u) => (
                <li key={u.fact} className="border-b border-border-subtle py-3 last:border-b-0">
                  <p className="font-ui text-[14px] text-text-primary">
                    <span className="mr-2 font-code text-[13px] text-score-warn" aria-hidden="true">?</span>
                    {u.fact}
                  </p>
                  {u.fix && <p className="mt-0.5 pl-5 font-ui text-[13px] text-text-secondary">{u.fix}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  )
}
