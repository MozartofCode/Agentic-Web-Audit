export const API_URL = import.meta.env.VITE_API_URL

async function request(path, options, fallbackMessage) {
  const response = await fetch(`${API_URL}${path}`, options)
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message = data?.detail || fallbackMessage
    throw new Error(typeof message === 'string' ? message : fallbackMessage)
  }

  return data
}

function postJson(path, body, fallbackMessage) {
  return request(
    path,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
    fallbackMessage,
  )
}

/**
 * Calls POST /analyze. `refresh` skips the 24h cache (Re-scan).
 * Throws an Error with a human-readable message on failure.
 */
export function analyzeProduct({ websiteUrl, githubUrl, refresh = false }) {
  return postJson(
    '/analyze',
    { website_url: websiteUrl || null, github_url: githubUrl || null, refresh },
    'Analysis failed, try again.',
  )
}

/** Calls GET /reports/{id} for a saved report (the /r/:id permalink). */
export function getReport(reportId) {
  return request(`/reports/${encodeURIComponent(reportId)}`, undefined, "Couldn't load that report.")
}

/** Calls POST /compare with two website URLs. Resolves to { reports: [a, b] }. */
export function compareSites(urlA, urlB) {
  return postJson('/compare', { website_urls: [urlA, urlB] }, 'Comparison failed, try again.')
}

/** Calls GET /leaderboard: ranked measured scores for well-known sites. */
export function getLeaderboard() {
  return request('/leaderboard', undefined, "Couldn't load the leaderboard.")
}

/** URL of the README badge for a domain. */
export function badgeUrl(domain) {
  return `${API_URL}/badge/${encodeURIComponent(domain)}.svg`
}
