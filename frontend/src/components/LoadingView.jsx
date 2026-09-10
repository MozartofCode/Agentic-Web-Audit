import { useEffect, useState } from 'react'

const STAGES = [
  { message: 'Crawling website...', duration: 3000, progressTo: 20 },
  { message: 'Reading GitHub repo...', duration: 3000, progressTo: 45 },
  { message: 'Analyzing with AI...', duration: 6000, progressTo: 80 },
  { message: 'Generating artifacts...', duration: 3000, progressTo: 100 },
]

function domainOf(url) {
  if (!url) return null
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export default function LoadingView({ websiteUrl, githubUrl }) {
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    if (stageIndex >= STAGES.length - 1) return undefined

    const timer = setTimeout(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1))
    }, STAGES[stageIndex].duration)

    return () => clearTimeout(timer)
  }, [stageIndex])

  const domains = [domainOf(websiteUrl), domainOf(githubUrl)].filter(Boolean)
  const stage = STAGES[stageIndex]
  const progress = stage.progressTo

  return (
    <section
      role="status"
      aria-live="polite"
      className="flex min-h-[calc(100vh-56px)] flex-col items-center justify-center px-6"
    >
      <div className="pulse-orb" aria-hidden="true" />

      <p key={stageIndex} className="stage-message fade-in mt-8 font-code text-[14px] text-text-secondary">
        {stage.message}
        <span className="blink-cursor text-accent">_</span>
      </p>

      <div className="mt-8 h-0.5 w-[320px] max-w-[90%] rounded-full bg-border-subtle">
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-[600ms] ease-out"
          style={{ width: `${progress}%`, boxShadow: '0 0 8px 1px var(--color-accent-glow)' }}
        />
      </div>

      {domains.length > 0 && (
        <p className="mt-6 font-code text-[12px] text-text-muted">{domains.join(' · ')}</p>
      )}
    </section>
  )
}
