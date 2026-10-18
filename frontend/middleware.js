/**
 * Vercel Routing Middleware: link-preview bots (Slack, X, LinkedIn, iMessage...) don't run
 * JavaScript, so for /r/:id they get the backend's /share/:id page, which carries the
 * report's Open Graph tags and image. Everyone else falls through to the SPA (vercel.json).
 */

export const config = { matcher: '/r/:id' }

const PREVIEW_BOTS =
  /bot|crawler|spider|preview|facebookexternalhit|slack|discord|whatsapp|telegram|linkedin|embedly|skype|vkshare|pinterest/i

export default async function middleware(request) {
  const userAgent = request.headers.get('user-agent') || ''
  const apiUrl = process.env.VITE_API_URL
  if (!apiUrl || !PREVIEW_BOTS.test(userAgent)) return undefined

  const id = new URL(request.url).pathname.split('/')[2]
  try {
    const share = await fetch(`${apiUrl}/share/${encodeURIComponent(id)}`)
    if (!share.ok) return undefined
    return new Response(await share.text(), {
      headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=3600' },
    })
  } catch {
    return undefined
  }
}
