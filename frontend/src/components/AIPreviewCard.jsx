export default function AIPreviewCard({ preview }) {
  const { summary, unknowns } = preview
  if (!summary && !unknowns.length) return null

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

      {unknowns.length > 0 && (
        <section className="mt-6">
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
  )
}
