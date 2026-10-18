import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { downloadFile } from '../download'
import { agentReadyTheme } from '../syntaxTheme'
import CopyButton from './CopyButton'

// Prism grammar names for languages the API sends under a different name.
const PRISM_LANGUAGE = { html: 'markup' }

export default function ArtifactSection({ files, platform }) {
  const [activeId, setActiveId] = useState(files[0]?.id)

  const activeFile = files.find((f) => f.id === activeId) || files[0]
  if (!activeFile) return null
  const content = activeFile.content || ''

  function handleTabChange(id) {
    setActiveId(id)
  }

  function handleDownload() {
    downloadFile(content, activeFile.filename)
  }

  return (
    <div className="overflow-hidden rounded border border-border-subtle bg-bg-surface">
      <div
        className="flex overflow-x-auto whitespace-nowrap border-b border-border-subtle"
        role="tablist"
      >
        {files.map((file) => {
          const isActive = file.id === activeFile.id
          return (
            <button
              key={file.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => handleTabChange(file.id)}
              className={`border-b-2 px-4 py-2.5 font-ui text-[14px] font-medium transition-colors duration-100 ${
                isActive
                  ? 'border-b-accent bg-bg-elevated text-text-primary'
                  : 'border-b-transparent text-text-muted hover:bg-bg-elevated/50 hover:text-text-secondary'
              }`}
            >
              {file.label}
              {file.developer && (
                <span className="ml-2 rounded border border-border-default px-1.5 py-px font-code text-[10px] text-text-muted">
                  dev
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div className="border-b border-border-subtle px-4 py-4">
        <p className="font-ui text-[13px] text-text-secondary">{activeFile.description}</p>
        {activeFile.how_to.length > 0 && (
          <div className="mt-3">
            <p className="font-ui text-[12px] font-medium uppercase tracking-wide text-text-muted">
              How to add this{platform ? ` on ${platform.name}` : ''}
            </p>
            <ol className="mt-2 list-decimal space-y-1 pl-5 font-ui text-[13px] text-text-secondary marker:font-code marker:text-text-muted">
              {activeFile.how_to.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        )}
      </div>

      <div className="flex h-11 items-center justify-between gap-2 border-b border-border-subtle bg-bg-surface px-4">
        <span className="truncate font-code text-[13px] text-text-secondary">{activeFile.filename}</span>
        <div className="flex shrink-0 gap-2">
          <CopyButton key={activeFile.id} text={content} />
          <button
            type="button"
            onClick={handleDownload}
            className="h-8 rounded border border-border-default bg-transparent px-3 font-ui text-[13px] font-medium text-text-secondary transition-colors duration-100 hover:border-border-strong hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            Download ↓
          </button>
        </div>
      </div>

      <div
        role="region"
        aria-label={`${activeFile.label} output`}
        className="code-viewer min-h-[240px] max-h-[640px] overflow-auto bg-bg-panel md:min-h-[360px]"
      >
        <SyntaxHighlighter
          language={PRISM_LANGUAGE[activeFile.language] || activeFile.language}
          style={agentReadyTheme}
          showLineNumbers
          customStyle={{ margin: 0, padding: '16px 0', background: 'transparent' }}
          lineNumberStyle={{
            minWidth: '44px',
            paddingRight: '16px',
            marginRight: '16px',
            borderRight: '1px solid rgba(255,255,255,0.07)',
            color: '#52525b',
            userSelect: 'none',
          }}
        >
          {content || 'Nothing to show here. The analysis didn\'t detect enough content to generate this file.'}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}
