/**
 * Tiny pathname router: / (home), /r/:id (saved report), /compare[/:a/:b] (side by side),
 * /leaderboard.
 */

const ID = '([A-Za-z0-9_-]{6,32})'
const REPORT = new RegExp(`^/r/${ID}/?$`)
const COMPARE = new RegExp(`^/compare(?:/${ID}/${ID})?/?$`)

export function parseRoute(pathname) {
  const report = pathname.match(REPORT)
  if (report) return { name: 'report', id: report[1] }
  const compare = pathname.match(COMPARE)
  if (compare) return { name: 'compare', ids: compare[1] ? [compare[1], compare[2]] : null }
  if (/^\/leaderboard\/?$/.test(pathname)) return { name: 'leaderboard' }
  return { name: 'home' }
}

export const LEADERBOARD_PATH = '/leaderboard'

export function reportPath(reportId) {
  return `/r/${reportId}`
}

export function comparePath(idA, idB) {
  return idA && idB ? `/compare/${idA}/${idB}` : '/compare'
}

/** Hostname without a leading www. — the key badges and deltas use. */
export function siteDomain(url) {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/**
 * Turn what someone typed ("python.org", "www.x.com/page", "https://x.com") into a full URL.
 * Returns { url } or { error } with a message to show under the field.
 */
export function normalizeUrl(input) {
  const raw = (input || '').trim()
  if (!raw) return { error: 'Enter a website address.' }
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`
  try {
    const url = new URL(withScheme)
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('scheme')
    if (!url.hostname.includes('.') && url.hostname !== 'localhost') throw new Error('host')
    return { url: url.href }
  } catch {
    return { error: `"${raw}" doesn't look like a website address. Try something like example.com.` }
  }
}
