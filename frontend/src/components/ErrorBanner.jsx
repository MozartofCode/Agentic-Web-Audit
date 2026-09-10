export default function ErrorBanner({ message }) {
  if (!message) return null

  return (
    <div
      role="alert"
      className="fade-in mt-4 flex items-start gap-3 rounded border border-score-bad/25 border-l-[3px] border-l-score-bad bg-score-bad-bg px-4 py-3"
    >
      <span className="mt-0.5 text-[14px] text-score-bad">⚠</span>
      <p className="font-ui text-[14px] font-medium text-text-primary">{message}</p>
    </div>
  )
}
