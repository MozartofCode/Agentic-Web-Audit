function pathOf(url) {
  try {
    const { pathname } = new URL(url)
    return pathname === '/' ? 'homepage' : pathname
  } catch {
    return url
  }
}

function QuestionRow({ question }) {
  const { answered, unverified, note } = question

  return (
    <li className="flex gap-3 border-b border-border-subtle py-3 last:border-b-0">
      <span
        className={`mt-0.5 w-4 shrink-0 text-center font-code text-[13px] font-medium ${answered ? 'text-score-good' : 'text-score-bad'}`}
        aria-label={answered ? 'Answered, quote verified' : 'Not answered'}
      >
        {answered ? '✓' : '✗'}
      </span>
      <div className="min-w-0">
        <p className="font-ui text-[14px] text-text-primary">{question.question}</p>
        {answered && (
          <>
            <p className="mt-0.5 font-ui text-[13px] text-text-secondary">{question.answer}</p>
            <p className="mt-1 break-words font-ui text-[12px] text-text-muted">
              {question.quote && <>“{question.quote}”{' '}</>}
              <a
                href={question.source}
                target="_blank"
                rel="noopener noreferrer"
                className="font-code underline decoration-border-strong underline-offset-2 hover:text-text-secondary"
              >
                {pathOf(question.source)}
              </a>
            </p>
          </>
        )}
        {!answered && note && <p className="mt-0.5 font-ui text-[13px] text-score-warn">{note}</p>}
        {!answered && !note && unverified && (
          <p className="mt-0.5 font-ui text-[13px] text-text-muted">
            The AI claimed an answer but couldn&apos;t quote your page, so it doesn&apos;t count.
            A real assistant would likely guess here.
          </p>
        )}
        {!answered && !note && !unverified && (
          <p className="mt-0.5 font-ui text-[13px] text-text-muted">
            Not in the text AI can read. Assistants will guess, or leave you out.
          </p>
        )}
      </div>
    </li>
  )
}

export default function BlindReaderCard({ questions }) {
  if (!questions.length) return null
  const answered = questions.filter((q) => q.answered).length

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-ui text-h2 font-semibold text-text-primary">Blind-reader test</h2>
        <span className="shrink-0 font-code text-[15px] font-medium text-text-primary">
          {answered}/{questions.length}
          <span className="ml-1 font-ui text-[12px] font-normal text-text-muted">answered</span>
        </span>
      </div>
      <p className="mt-1 font-ui text-small text-text-secondary">
        We gave an AI only the raw HTML a crawler receives (no JavaScript) and asked the same
        eight questions customers ask about any business. An answer only counts if the AI
        quoted your page and we found that exact quote on it. Not part of your score.
      </p>
      <ul className="mt-3">
        {questions.map((q) => (
          <QuestionRow key={q.id || q.question} question={q} />
        ))}
      </ul>
    </div>
  )
}
