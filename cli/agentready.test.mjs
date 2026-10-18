import assert from 'node:assert/strict'
import { mkdtempSync, readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'

import { EXIT_BELOW_MIN, EXIT_ERROR, EXIT_OK, formatReport, main, parseArgs } from './agentready.mjs'

const RESULT = {
  product_name: 'Acme',
  website_url: 'https://acme.test/',
  github_url: null,
  report_id: 'abc12345',
  audit: {
    overall: 62,
    grade: 'D',
    critical_failures: [],
    categories: [
      { id: 'crawler', label: 'AI crawler access', score: 90 },
      { id: 'developer', label: 'Developer & API', score: null },
    ],
    top_fixes: [
      { title: 'Publish llms.txt', points: 5, effort: 'minutes', evidence: 'No /llms.txt found.' },
    ],
  },
}

function sink() {
  let text = ''
  return { write: (s) => { text += s }, get text() { return text } }
}

async function withServer(handler, fn) {
  const server = createServer(handler)
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  try {
    return await fn(`http://127.0.0.1:${server.address().port}`)
  } finally {
    server.close()
  }
}

test('parseArgs reads options and env defaults', () => {
  const opts = parseArgs(['https://a.test', '--min-score', '70', '--refresh'], {
    AGENTREADY_API_URL: 'https://api.test/',
  })
  assert.equal(opts.url, 'https://a.test')
  assert.equal(opts.minScore, 70)
  assert.equal(opts.refresh, true)
  assert.equal(opts.api, 'https://api.test')
})

test('parseArgs rejects bad input', () => {
  assert.throws(() => parseArgs([]), /required/)
  assert.throws(() => parseArgs(['https://a.test', '--min-score', '101']), /0 to 100/)
  assert.throws(() => parseArgs(['https://a.test', '--min-score']), /needs a value/)
  assert.throws(() => parseArgs(['https://a.test', '--nope']), /Unknown option/)
})

test('formatReport shows score, n/a categories, fixes and the report link', () => {
  const text = formatReport(RESULT, { app: 'https://app.test' })
  assert.match(text, /62\/100 \(D\)/)
  assert.match(text, /Developer & API\s+n\/a/)
  assert.match(text, /1\. Publish llms\.txt\s+\(\+5 pts, minutes\)/)
  assert.match(text, /https:\/\/app\.test\/r\/abc12345/)
})

test('main exits 1 below the minimum and writes GitHub outputs and summary', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'agentready-'))
  const env = { GITHUB_OUTPUT: join(dir, 'out'), GITHUB_STEP_SUMMARY: join(dir, 'summary') }
  let body
  await withServer(
    (req, res) => {
      let raw = ''
      req.on('data', (c) => { raw += c })
      req.on('end', () => {
        body = JSON.parse(raw)
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify(RESULT))
      })
    },
    async (api) => {
      const out = sink()
      const err = sink()
      const code = await main(
        ['https://acme.test', '--api', api, '--app', 'https://app.test', '--min-score', '70'],
        env, out, err,
      )
      assert.equal(code, EXIT_BELOW_MIN)
      assert.match(err.text, /below the minimum of 70/)
    },
  )
  assert.deepEqual(body, { website_url: 'https://acme.test', github_url: null, refresh: false })
  assert.match(readFileSync(env.GITHUB_OUTPUT, 'utf8'), /score=62\ngrade=D\nreport-url=https:\/\/app\.test\/r\/abc12345/)
  assert.match(readFileSync(env.GITHUB_STEP_SUMMARY, 'utf8'), /❌ Below the minimum score of 70/)
})

test('main passes when the score meets the minimum', async () => {
  await withServer(
    (req, res) => {
      req.resume()
      req.on('end', () => {
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify(RESULT))
      })
    },
    async (api) => {
      const code = await main(['https://acme.test', '--api', api, '--min-score', '60'], {}, sink(), sink())
      assert.equal(code, EXIT_OK)
    },
  )
})

test('main surfaces the API error detail and exits 2', async () => {
  await withServer(
    (req, res) => {
      req.resume()
      req.on('end', () => {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ detail: 'That URL points to a private network address.' }))
      })
    },
    async (api) => {
      const err = sink()
      const code = await main(['http://10.0.0.1', '--api', api], {}, sink(), err)
      assert.equal(code, EXIT_ERROR)
      assert.match(err.text, /private network address/)
    },
  )
})

test('main reports an unreachable API', async () => {
  const err = sink()
  const code = await main(['https://acme.test', '--api', 'http://127.0.0.1:9'], {}, sink(), err)
  assert.equal(code, EXIT_ERROR)
  assert.match(err.text, /Could not reach the AgentReady API/)
})
