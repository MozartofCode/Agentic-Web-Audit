const PURPOSE_LABEL = {
  search: 'AI search',
  user: 'Fetches for a user',
  training: 'Model training',
}

const STATUS_STYLE = {
  allowed: 'border-score-good/40 text-score-good',
  partial: 'border-score-warn/40 text-score-warn',
  blocked: 'border-score-bad/40 text-score-bad',
}

function BotRow({ entry }) {
  return (
    <li className="flex items-center justify-between gap-3 border-b border-border-subtle py-2.5 last:border-b-0">
      <div className="min-w-0">
        <p className="font-code text-[13px] text-text-primary">{entry.bot}</p>
        <p className="truncate font-ui text-[12px] text-text-muted" title={entry.detail}>
          {entry.owner} · {entry.status === 'partial' ? entry.detail : PURPOSE_LABEL[entry.purpose]}
        </p>
      </div>
      <span
        className={`shrink-0 rounded border px-2 py-0.5 font-code text-[11px] ${STATUS_STYLE[entry.status]}`}
      >
        {entry.status}
      </span>
    </li>
  )
}

export default function CrawlerMatrix({ entries }) {
  if (!entries.length) return null

  const answerBots = entries.filter((e) => e.purpose !== 'training')
  const trainingBots = entries.filter((e) => e.purpose === 'training')

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <h2 className="font-ui text-h2 font-semibold text-text-primary">Who can read your site</h2>
      <p className="mt-1 font-ui text-small text-text-secondary">
        What your robots.txt tells each AI crawler. Blocking training bots is a valid choice;
        blocking search and assistant bots means AI can't look you up when someone asks.
      </p>

      <div className="mt-5 grid gap-6 md:grid-cols-2">
        <section>
          <h3 className="font-ui text-[13px] font-medium text-text-primary">
            Search &amp; assistant bots
          </h3>
          <ul className="mt-2">
            {answerBots.map((entry) => (
              <BotRow key={entry.bot} entry={entry} />
            ))}
          </ul>
        </section>
        <section>
          <h3 className="font-ui text-[13px] font-medium text-text-primary">Training bots</h3>
          <ul className="mt-2">
            {trainingBots.map((entry) => (
              <BotRow key={entry.bot} entry={entry} />
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
