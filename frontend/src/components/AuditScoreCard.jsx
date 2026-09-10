import { useEffect, useRef } from 'react'

const CHECKS = [
  { key: 'has_api', label: 'Has public API', points: 20 },
  { key: 'has_llms_txt', label: 'Has llms.txt', points: 15 },
  { key: 'has_openapi_spec', label: 'Has OpenAPI spec', points: 20 },
  { key: 'has_structured_docs', label: 'Has structured docs', points: 15 },
  { key: 'has_api_key_auth', label: 'API key auth', points: 15 },
  { key: 'has_webhook_support', label: 'Webhook support', points: 15 },
]

function scoreColorClass(score) {
  if (score >= 70) return 'text-score-good'
  if (score >= 40) return 'text-score-warn'
  return 'text-score-bad'
}

export default function AuditScoreCard({ auditScore }) {
  const scoreRef = useRef(null)
  const { score, total, breakdown } = auditScore

  useEffect(() => {
    const el = scoreRef.current
    if (!el) return undefined

    const duration = 1200
    const start = performance.now()
    let frameId

    function frame(now) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 4)
      el.textContent = Math.round(eased * score)
      if (progress < 1) frameId = requestAnimationFrame(frame)
    }

    frameId = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(frameId)
  }, [score])

  return (
    <div className="rounded border border-border-subtle bg-bg-surface p-6">
      <h2 className="text-center font-ui text-h2 font-semibold text-text-primary">
        Agent Readiness Score
      </h2>

      <div
        className="mt-4 text-center"
        aria-label={`Agent readiness score: ${score} out of ${total}`}
      >
        <span
          ref={scoreRef}
          className={`font-code text-[5rem] font-medium leading-none ${scoreColorClass(score)}`}
        >
          0
        </span>
        <span className="ml-1 font-code text-[1.25rem] text-text-muted">/{total}</span>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {CHECKS.map((check) => {
          const passed = Boolean(breakdown[check.key])
          return (
            <div
              key={check.key}
              className={`rounded border border-border-subtle bg-bg-surface p-3 pl-4 ${
                passed ? 'border-l-2 border-l-score-good' : 'border-l-2 border-l-score-bad'
              }`}
            >
              <p className="font-ui text-[13px] font-medium text-text-primary">
                <span className={passed ? 'text-score-good' : 'text-score-bad'} aria-hidden="true">
                  {passed ? '✓' : '✗'}
                </span>{' '}
                {check.label}
              </p>
              <p className="mt-1 font-code text-[12px] text-text-muted">{check.points} pts</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
