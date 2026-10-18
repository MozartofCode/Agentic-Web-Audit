import { STATUS_ORDER, scoreTextClass } from '../status'
import CheckItem from './CheckItem'

function CategorySection({ category, checks }) {
  const applicable = checks
    .filter((c) => c.status !== 'na')
    .sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) || b.weight - a.weight)
  const skipped = checks.filter((c) => c.status === 'na')

  return (
    <section id={`category-${category.id}`} className="scroll-mt-20">
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-ui text-[16px] font-semibold text-text-primary">{category.label}</h3>
          <p className="font-ui text-small text-text-muted">{category.description}</p>
        </div>
        <span className={`shrink-0 font-code text-[15px] font-medium ${scoreTextClass(category.score)}`}>
          {category.score === null ? 'n/a' : `${category.score}/100`}
        </span>
      </div>

      {applicable.length > 0 && (
        <div className="mt-3 space-y-2">
          {applicable.map((check) => (
            <CheckItem key={check.id} check={check} />
          ))}
        </div>
      )}

      {skipped.length > 0 && (
        <p className="mt-2 font-ui text-[12px] text-text-muted">
          {applicable.length === 0 ? skipped[0].evidence : `Skipped (not applicable): ${skipped.map((c) => c.title).join(' · ')}`}
        </p>
      )}
    </section>
  )
}

export default function CheckList({ categories, checks }) {
  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <h2 className="font-ui text-h2 font-semibold text-text-primary">Every check, with evidence</h2>
      <p className="mt-1 font-ui text-small text-text-secondary">
        Failures first. Open any check to see what we found and a fix you can copy.
      </p>
      <div className="mt-6 space-y-8">
        {categories.map((category) => (
          <CategorySection
            key={category.id}
            category={category}
            checks={checks.filter((c) => c.category === category.id)}
          />
        ))}
      </div>
    </div>
  )
}
