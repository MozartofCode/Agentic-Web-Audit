import { scoreStrokeClass, scoreTextClass } from '../status'

const RADIUS = 26
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function Ring({ category }) {
  const { score, label } = category
  const filled = score === null ? 0 : (score / 100) * CIRCUMFERENCE

  return (
    <a
      href={`#category-${category.id}`}
      className="flex flex-col items-center gap-2 rounded p-2 text-center transition-colors duration-100 hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30"
    >
      <div className="relative h-16 w-16">
        <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90" aria-hidden="true">
          <circle cx="32" cy="32" r={RADIUS} fill="none" strokeWidth="5" className="stroke-border-subtle" />
          <circle
            cx="32"
            cy="32"
            r={RADIUS}
            fill="none"
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
            className={scoreStrokeClass(score)}
          />
        </svg>
        <span
          className={`absolute inset-0 flex items-center justify-center font-code text-[15px] font-medium ${scoreTextClass(score)}`}
        >
          {score === null ? 'n/a' : score}
        </span>
      </div>
      <span className="font-ui text-[12px] leading-tight text-text-secondary">{label}</span>
    </a>
  )
}

export default function CategoryRings({ categories }) {
  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
      {categories.map((category) => (
        <Ring key={category.id} category={category} />
      ))}
    </div>
  )
}
