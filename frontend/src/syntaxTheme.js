/** Custom react-syntax-highlighter theme matching the AgentReady design system (UI.md). */
export const agentReadyTheme = {
  'code[class*="language-"]': {
    color: '#e4e4e7',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    lineHeight: '1.7',
    background: 'transparent',
  },
  'pre[class*="language-"]': {
    color: '#e4e4e7',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    lineHeight: '1.7',
    background: 'transparent',
  },
  comment: { color: '#52525b' },
  keyword: { color: '#06b6d4' },
  string: { color: '#86efac' },
  number: { color: '#fca5a5' },
  function: { color: '#c4b5fd' },
  operator: { color: '#94a3b8' },
  property: { color: '#7dd3fc' },
  punctuation: { color: '#52525b' },
}
