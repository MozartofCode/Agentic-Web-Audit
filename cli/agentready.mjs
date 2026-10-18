#!/usr/bin/env node
/**
 * AgentReady CLI — scan a website from the terminal or CI and fail the build if its
 * AI-readiness score drops below a threshold.
 *
 *   agentready https://example.com --min-score 70
 *
 * Talks to an AgentReady backend (POST /analyze). No dependencies; Node 18+.
 * Exit codes: 0 = ok, 1 = score below --min-score, 2 = usage or scan error.
 */

import { appendFileSync, realpathSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

export const EXIT_OK = 0
export const EXIT_BELOW_MIN = 1
export const EXIT_ERROR = 2

const USAGE = `Usage: agentready <website-url> [options]

Options:
  --min-score <n>   Exit 1 if the overall score is below n (0-100)
  --github <url>    Also analyze a public GitHub repo
  --api <url>       AgentReady backend URL (or AGENTREADY_API_URL)
  --app <url>       AgentReady web app URL, for report links (or AGENTREADY_APP_URL)
  --refresh         Skip the server's 24h cache and rescan
  --json            Print the raw JSON response
  -h, --help        Show this help
`

/** Parse argv into options. Throws Error with a user-facing message on bad input. */
export function parseArgs(argv, env = {}) {
  const opts = {
    url: null,
    github: null,
    minScore: null,
    api: env.AGENTREADY_API_URL || 'http://localhost:8000',
    app: env.AGENTREADY_APP_URL || null,
    refresh: false,
    json: false,
    help: false,
  }
  const takesValue = { '--min-score': 'minScore', '--github': 'github', '--api': 'api', '--app': 'app' }

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg === '-h' || arg === '--help') opts.help = true
    else if (arg === '--refresh') opts.refresh = true
    else if (arg === '--json') opts.json = true
    else if (arg in takesValue) {
      const value = argv[++i]
      if (value === undefined || value.startsWith('--')) throw new Error(`${arg} needs a value`)
      opts[takesValue[arg]] = value
    } else if (arg.startsWith('-')) throw new Error(`Unknown option: ${arg}`)
    else if (!opts.url) opts.url = arg
    else throw new Error(`Unexpected argument: ${arg}`)
  }

  if (opts.help) return opts
  if (!opts.url && !opts.github) throw new Error('A website URL is required')
  if (opts.minScore !== null) {
    const n = Number(opts.minScore)
    if (!Number.isInteger(n) || n < 0 || n > 100) {
      throw new Error('--min-score must be a whole number from 0 to 100')
    }
    opts.minScore = n
  }
  opts.api = opts.api.replace(/\/+$/, '')
  if (opts.app) opts.app = opts.app.replace(/\/+$/, '')
  return opts
}

/** POST /analyze. Throws Error with the server's human-readable detail on failure. */
export async function analyze(opts, fetchImpl = fetch) {
  let response
  try {
    response = await fetchImpl(`${opts.api}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        website_url: opts.url,
        github_url: opts.github,
        refresh: opts.refresh,
      }),
    })
  } catch (err) {
    throw new Error(`Could not reach the AgentReady API at ${opts.api} (${err.message})`)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : `HTTP ${response.status}`
    throw new Error(detail)
  }
  return data
}

export function reportUrl(result, appUrl) {
  return appUrl && result.report_id ? `${appUrl}/r/${result.report_id}` : null
}

function bar(score, width = 20) {
  const filled = Math.round((score / 100) * width)
  return '█'.repeat(filled) + '░'.repeat(width - filled)
}

/** Plain-text report for the terminal. */
export function formatReport(result, opts) {
  const { audit } = result
  const lines = [
    '',
    `${result.product_name} — AI readiness ${audit.overall}/100 (${audit.grade})`,
    '',
  ]
  for (const c of audit.categories) {
    const score = c.score === null ? '  n/a' : String(c.score).padStart(5)
    lines.push(`  ${c.label.padEnd(30)} ${c.score === null ? ' '.repeat(20) : bar(c.score)} ${score}`)
  }
  if (audit.critical_failures?.length) {
    lines.push('', `  Critical: ${audit.critical_failures.join('; ')} (score capped)`)
  }
  if (audit.top_fixes?.length) {
    lines.push('', 'Top fixes:')
    audit.top_fixes.forEach((fix, i) => {
      lines.push(`  ${i + 1}. ${fix.title}  (+${fix.points} pts, ${fix.effort})`)
      lines.push(`     ${fix.evidence}`)
    })
  }
  const link = reportUrl(result, opts.app)
  if (link) lines.push('', `Full report: ${link}`)
  return lines.join('\n') + '\n'
}

/** Markdown for the GitHub Actions job summary. */
export function formatSummary(result, opts) {
  const { audit } = result
  const lines = [
    `## AgentReady: ${audit.overall}/100 (${audit.grade})`,
    '',
    `**${result.product_name}** — ${result.website_url || result.github_url || ''}`,
    '',
    '| Category | Score |',
    '|---|---|',
    ...audit.categories.map((c) => `| ${c.label} | ${c.score === null ? 'n/a' : c.score} |`),
  ]
  if (audit.top_fixes?.length) {
    lines.push('', '### Top fixes', '')
    audit.top_fixes.forEach((fix, i) => {
      lines.push(`${i + 1}. **${fix.title}** (+${fix.points} pts, ${fix.effort}) — ${fix.evidence}`)
    })
  }
  const link = reportUrl(result, opts.app)
  if (link) lines.push('', `[Full report](${link})`)
  if (opts.minScore !== null) {
    const ok = audit.overall >= opts.minScore
    lines.push('', ok ? `✅ Meets the minimum score of ${opts.minScore}.` : `❌ Below the minimum score of ${opts.minScore}.`)
  }
  return lines.join('\n') + '\n'
}

export function exitCodeFor(result, minScore) {
  return minScore !== null && result.audit.overall < minScore ? EXIT_BELOW_MIN : EXIT_OK
}

/** In GitHub Actions, write step outputs and the job summary. */
function writeGithubOutputs(result, opts, env) {
  if (env.GITHUB_OUTPUT) {
    const link = reportUrl(result, opts.app) || ''
    appendFileSync(
      env.GITHUB_OUTPUT,
      `score=${result.audit.overall}\ngrade=${result.audit.grade}\nreport-url=${link}\n`,
    )
  }
  if (env.GITHUB_STEP_SUMMARY) appendFileSync(env.GITHUB_STEP_SUMMARY, formatSummary(result, opts))
}

export async function main(argv, env = process.env, out = process.stdout, err = process.stderr) {
  let opts
  try {
    opts = parseArgs(argv, env)
  } catch (e) {
    err.write(`agentready: ${e.message}\n\n${USAGE}`)
    return EXIT_ERROR
  }
  if (opts.help) {
    out.write(USAGE)
    return EXIT_OK
  }

  let result
  try {
    result = await analyze(opts)
  } catch (e) {
    err.write(`agentready: ${e.message}\n`)
    return EXIT_ERROR
  }

  out.write(opts.json ? JSON.stringify(result, null, 2) + '\n' : formatReport(result, opts))
  writeGithubOutputs(result, opts, env)

  const code = exitCodeFor(result, opts.minScore)
  if (code === EXIT_BELOW_MIN) {
    err.write(`agentready: score ${result.audit.overall} is below the minimum of ${opts.minScore}\n`)
  }
  return code
}

function isEntryPoint() {
  // npm installs bins as symlinks, so compare real paths.
  try {
    return import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href
  } catch {
    return false
  }
}

if (isEntryPoint()) {
  main(process.argv.slice(2)).then((code) => {
    process.exitCode = code
  })
}
