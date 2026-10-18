import { useEffect, useRef } from 'react'
import { scoreTextClass } from '../status'
import CategoryRings from './CategoryRings'

export default function ScoreHero({ audit }) {
  const scoreRef = useRef(null)
  const { overall, grade, categories, critical_failures: criticalFailures } = audit

  useEffect(() => {
    const el = scoreRef.current
    if (!el) return undefined

    const duration = 1200
    const start = performance.now()
    let frameId

    function frame(now) {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 4)
      el.textContent = Math.round(eased * overall)
      if (progress < 1) frameId = requestAnimationFrame(frame)
    }

    frameId = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(frameId)
  }, [overall])

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <h2 className="text-center font-ui text-h2 font-semibold text-text-primary">
        AI Readiness Score
      </h2>
      <p className="mt-1 text-center font-ui text-small text-text-muted">
        Measured from your live site — every point links to the evidence below.
      </p>

      <div className="mt-4 flex items-end justify-center gap-4" aria-label={`Score ${overall} out of 100, grade ${grade}`}>
        <div>
          <span ref={scoreRef} className={`font-code text-[5rem] font-medium leading-none ${scoreTextClass(overall)}`}>
            0
          </span>
          <span className="ml-1 font-code text-[1.25rem] text-text-muted">/100</span>
        </div>
        <span
          className={`mb-2 rounded border border-border-default px-3 py-1 font-code text-[1.5rem] font-medium ${scoreTextClass(overall)}`}
        >
          {grade}
        </span>
      </div>

      {criticalFailures.length > 0 && (
        <p className="mx-auto mt-4 max-w-[560px] rounded border border-score-bad/30 bg-score-bad-bg px-4 py-3 text-center font-ui text-small text-text-secondary">
          <span className="font-medium text-score-bad">Score capped at 49.</span> A critical
          check failed: {criticalFailures.map((title) => `“${title}”`).join(' and ')}. Until
          it's fixed, AI can't really read your site, so nothing else counts for much.
        </p>
      )}

      <div className="mt-8">
        <CategoryRings categories={categories} />
      </div>
    </div>
  )
}
