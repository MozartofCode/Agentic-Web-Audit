import { useEffect, useState } from 'react'

const STAGES = [
  { message: 'Reading robots.txt, sitemap and llms.txt...', duration: 2000, progressTo: 20 },
  { message: 'Testing access as an AI crawler...', duration: 2000, progressTo: 35 },
  { message: 'Fetching key pages...', duration: 3000, progressTo: 55 },
  { message: 'Running 37 checks...', duration: 2000, progressTo: 70 },
  { message: 'Asking AI how it understands you...', duration: 5000, progressTo: 90 },
  { message: 'Generating your fix-it pack...', duration: 3000, progressTo: 100 },
]

function domainOf(url) {
  if (!url) return null
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

/** `message` replaces the scan stages (e.g. while fetching a saved report). */
export default function LoadingView({ urls = [], message = '' }) {
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    if (message || stageIndex >= STAGES.length - 1) return undefined

    const timer = setTimeout(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1))
    }, STAGES[stageIndex].duration)

    return () => clearTimeout(timer)
  }, [stageIndex, message])

  const domains = urls.map((u) => domainOf(u.trim())).filter(Boolean)
  const stage = STAGES[stageIndex]
  const progress = stage.progressTo

  return (
    <section
      role="status"
      aria-live="polite"
      className="flex min-h-[calc(100vh-56px)] flex-col items-center justify-center px-6"
    >
      <div className="pulse-orb" aria-hidden="true" />

      <p key={message || stageIndex} className="stage-message fade-in mt-8 font-code text-[14px] text-text-secondary">
        {message || stage.message}
        <span className="blink-cursor text-accent">_</span>
      </p>

      {!message && (
        <div className="mt-8 h-0.5 w-[320px] max-w-[90%] rounded-full bg-border-subtle">
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-[600ms] ease-out"
            style={{ width: `${progress}%`, boxShadow: '0 0 8px 1px var(--color-accent-glow)' }}
          />
        </div>
      )}

      {domains.length > 0 && (
        <p className="mt-6 font-code text-[12px] text-text-muted">{domains.join(' · ')}</p>
      )}
    </section>
  )
}
