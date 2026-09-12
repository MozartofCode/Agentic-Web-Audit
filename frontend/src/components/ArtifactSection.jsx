import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { downloadFile } from '../download'
import { agentReadyTheme } from '../syntaxTheme'

const TABS = [
  { key: 'llms_txt', label: 'llms.txt', filename: 'llms.txt', language: 'markdown' },
  { key: 'audit_md', label: 'Audit Report', filename: 'audit-report.md', language: 'markdown' },
  { key: 'mcp_server_ts', label: 'MCP Server', filename: 'mcp_server.ts', language: 'typescript' },
  { key: 'openapi_yaml', label: 'OpenAPI Spec', filename: 'openapi.yaml', language: 'yaml' },
]

export default function ArtifactSection({ artifacts }) {
  const [activeKey, setActiveKey] = useState(TABS[0].key)
  const [copied, setCopied] = useState(false)

  const activeTab = TABS.find((t) => t.key === activeKey)
  const content = artifacts[activeKey] || ''

  function handleTabChange(key) {
    setActiveKey(key)
    setCopied(false)
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard permissions denied — nothing to fall back to for MVP.
    }
  }

  function handleDownload() {
    downloadFile(content, activeTab.filename)
  }

  return (
    <div className="overflow-hidden rounded border border-border-subtle bg-bg-surface">
      <div
        className="flex overflow-x-auto whitespace-nowrap border-b border-border-subtle"
        role="tablist"
      >
        {TABS.map((tab) => {
          const isActive = tab.key === activeKey
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => handleTabChange(tab.key)}
              className={`border-b-2 px-4 py-2.5 font-ui text-[14px] font-medium transition-colors duration-100 ${
                isActive
                  ? 'border-b-accent bg-bg-elevated text-text-primary'
                  : 'border-b-transparent text-text-muted hover:bg-bg-elevated/50 hover:text-text-secondary'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="flex h-11 items-center justify-between border-b border-border-subtle bg-bg-surface px-4">
        <span className="font-code text-[13px] text-text-secondary">{activeTab.filename}</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="h-8 rounded border border-border-default bg-transparent px-3 font-ui text-[13px] font-medium text-text-secondary transition-colors duration-100 hover:border-border-strong hover:bg-bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
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
        aria-label={`${activeTab.label} output`}
        className="code-viewer min-h-[320px] max-h-[640px] overflow-auto bg-bg-panel md:min-h-[480px]"
      >
        <SyntaxHighlighter
          language={activeTab.language}
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
