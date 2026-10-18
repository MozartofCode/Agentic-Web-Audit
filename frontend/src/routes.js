/** Tiny pathname router: / (home), /r/:id (saved report), /compare[/:a/:b] (side by side). */

const ID = '([A-Za-z0-9_-]{6,32})'
const REPORT = new RegExp(`^/r/${ID}/?$`)
const COMPARE = new RegExp(`^/compare(?:/${ID}/${ID})?/?$`)

export function parseRoute(pathname) {
  const report = pathname.match(REPORT)
  if (report) return { name: 'report', id: report[1] }
  const compare = pathname.match(COMPARE)
  if (compare) return { name: 'compare', ids: compare[1] ? [compare[1], compare[2]] : null }
  return { name: 'home' }
}

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
