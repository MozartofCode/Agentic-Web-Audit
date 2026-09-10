import { useState } from 'react'
import { analyzeProduct } from './api'
import Header from './components/Header'
import LandingView from './components/LandingView'
import LoadingView from './components/LoadingView'
import ResultsView from './components/ResultsView'

export default function App() {
  const [appState, setAppState] = useState('idle') // 'idle' | 'loading' | 'done' | 'error'
  const [results, setResults] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [validationError, setValidationError] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [elapsedSeconds, setElapsedSeconds] = useState(null)

  async function handleSubmit() {
    if (!websiteUrl.trim() && !githubUrl.trim()) {
      setValidationError('At least one URL is required.')
      return
    }

    setValidationError('')
    setErrorMsg('')
    setAppState('loading')

    const startedAt = performance.now()

    try {
      const data = await analyzeProduct({ websiteUrl: websiteUrl.trim(), githubUrl: githubUrl.trim() })
      setElapsedSeconds(Math.round((performance.now() - startedAt) / 1000))
      setResults(data)
      setAppState('done')
    } catch (err) {
      setErrorMsg(err.message || 'Analysis failed, try again.')
      setAppState('error')
    }
  }

  function handleNewAnalysis() {
    setAppState('idle')
    setResults(null)
    setErrorMsg('')
    setValidationError('')
    setWebsiteUrl('')
    setGithubUrl('')
    setElapsedSeconds(null)
  }

  return (
    <div className="min-h-screen bg-bg-base">
      <Header showNewAnalysis={appState === 'done'} onNewAnalysis={handleNewAnalysis} />

      <main className="pt-14">
        {appState === 'loading' && <LoadingView websiteUrl={websiteUrl} githubUrl={githubUrl} />}

        {(appState === 'idle' || appState === 'error') && (
          <LandingView
            websiteUrl={websiteUrl}
            githubUrl={githubUrl}
            onWebsiteChange={setWebsiteUrl}
            onGithubChange={setGithubUrl}
            onSubmit={handleSubmit}
            loading={false}
            validationError={validationError}
            errorMsg={errorMsg}
          />
        )}

        {appState === 'done' && results && (
          <ResultsView
            results={results}
            websiteUrl={websiteUrl}
            githubUrl={githubUrl}
            elapsedSeconds={elapsedSeconds}
          />
        )}
      </main>
    </div>
  )
}
