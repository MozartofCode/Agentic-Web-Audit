import { useState } from 'react'

export default function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard permissions denied — nothing to fall back to for MVP.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="h-8 shrink-0 rounded border border-border-default bg-transparent px-3 font-ui text-[13px] font-medium text-text-secondary transition-colors duration-100 hover:border-border-strong hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30"
    >
      {copied ? '✓ Copied' : label}
    </button>
  )
}
