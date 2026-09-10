const API_URL = import.meta.env.VITE_API_URL

/**
 * Calls POST /analyze. Throws an Error with a human-readable message on failure.
 */
export async function analyzeProduct({ websiteUrl, githubUrl }) {
  const response = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      website_url: websiteUrl || null,
      github_url: githubUrl || null,
    }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message = data?.detail || 'Analysis failed, try again.'
    throw new Error(typeof message === 'string' ? message : 'Analysis failed, try again.')
  }

  return data
}
