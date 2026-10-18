import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeProduct, compareSites, getReport } from './api'
import { LEADERBOARD_PATH, comparePath, parseRoute, reportPath, siteDomain } from './routes'
import CompareForm from './components/CompareForm'
import CompareView from './components/CompareView'
import Header from './components/Header'
import LandingView from './components/LandingView'
import LeaderboardView from './components/LeaderboardView'
import LoadingView from './components/LoadingView'
import ResultsView from './components/ResultsView'

/** What is on screen for a route, so a URL is only loaded when it isn't shown already. */
function routeKey(route) {
  if (route.name === 'report') return `report:${route.id}`
  if (route.name === 'compare' && route.ids) return `compare:${route.ids.join(':')}`
  return route.name
}

export default function App() {
  const [appState, setAppState] = useState('idle') // 'idle' | 'loading' | 'done' | 'error'
  const [results, setResults] = useState(null) // one report
  const [comparison, setComparison] = useState(null) // [reportA, reportB]
  const [errorMsg, setErrorMsg] = useState('')
  const [validationError, setValidationError] = useState('')
  const [inputMode, setInputMode] = useState('website') // 'website' | 'github'
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [compareUrls, setCompareUrls] = useState(['', ''])
  const [loadingMessage, setLoadingMessage] = useState('') // static message for saved reports
  const [route, setRoute] = useState(() => parseRoute(window.location.pathname))
  const [shownKey, setShownKey] = useState(null)
  const requestedKey = useRef(null) // the newest route/result asked for; older loads are dropped

  const markShown = useCallback((key) => {
    requestedKey.current = key
    setShownKey(key)
  }, [])

  const navigate = useCallback((path) => {
    if (window.location.pathname !== path) window.history.pushState(null, '', path)
    setRoute(parseRoute(path))
    window.scrollTo(0, 0)
  }, [])

  useEffect(() => {
    function handlePopState() {
      setRoute(parseRoute(window.location.pathname))
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Load a permalink (/r/:id, /compare/:a/:b) when it isn't already on screen.
  useEffect(() => {
    const key = routeKey(route)
    if (key === shownKey) return

    async function load() {
      markShown(key)
      setErrorMsg('')
      setValidationError('')
      if (route.name !== 'report' && !(route.name === 'compare' && route.ids)) {
        setAppState('idle')
        return
      }

      setLoadingMessage(route.name === 'report' ? 'Loading saved report...' : 'Loading comparison...')
      setAppState('loading')
      try {
        if (route.name === 'report') {
          const data = await getReport(route.id)
          if (requestedKey.current !== key) return
          setResults(data)
        } else {
          const reports = await Promise.all(route.ids.map(getReport))
          if (requestedKey.current !== key) return
          setComparison(reports)
        }
        setAppState('done')
      } catch (err) {
        if (requestedKey.current !== key) return
        setErrorMsg(err.message || "Couldn't load that report.")
        setAppState('error')
      }
    }

    load()
  }, [route, shownKey, markShown])

  useEffect(() => {
    if (appState === 'done' && route.name === 'compare' && comparison) {
      const [a, b] = comparison.map((r) => siteDomain(r.website_url))
      document.title = `${a} vs ${b} — AgentReady`
    } else if (appState === 'done' && results) {
      const name = siteDomain(results.website_url) || results.product_name
      document.title = `${name} · ${results.audit.overall}/100 — AgentReady`
    } else {
      document.title = 'AgentReady'
    }
  }, [appState, route, results, comparison])

  const runAnalysis = useCallback(
    async ({ website, github, refresh = false }) => {
      setErrorMsg('')
      setLoadingMessage('')
      setWebsiteUrl(website)
      setGithubUrl(github)
      setAppState('loading')

      try {
        const data = await analyzeProduct({ websiteUrl: website, githubUrl: github, refresh })
        setResults(data)
        setAppState('done')
        markShown(data.report_id ? `report:${data.report_id}` : 'home')
        navigate(data.report_id ? reportPath(data.report_id) : '/')
      } catch (err) {
        setErrorMsg(err.message || 'Analysis failed, try again.')
        setAppState('error')
      }
    },
    [navigate, markShown],
  )

  function handleSubmit() {
    const activeUrl = inputMode === 'website' ? websiteUrl.trim() : githubUrl.trim()
    if (!activeUrl) {
      setValidationError('A URL is required.')
      return
    }
    setValidationError('')
    runAnalysis({
      website: inputMode === 'website' ? activeUrl : '',
      github: inputMode === 'github' ? activeUrl : '',
    })
  }

  function handleRescan() {
    setInputMode(results.website_url ? 'website' : 'github')
    runAnalysis({
      website: results.website_url || '',
      github: results.github_url || '',
      refresh: true,
    })
  }

  async function handleCompare() {
    const [a, b] = compareUrls.map((u) => u.trim())
    if (!a || !b) {
      setValidationError('Enter both sites.')
      return
    }
    setValidationError('')
    setErrorMsg('')
    setLoadingMessage('')
    setAppState('loading')

    try {
      const data = await compareSites(a, b)
      setComparison(data.reports)
      setAppState('done')
      const [idA, idB] = data.reports.map((r) => r.report_id)
      if (idA && idB) {
        markShown(`compare:${idA}:${idB}`)
        navigate(comparePath(idA, idB))
      }
    } catch (err) {
      setErrorMsg(err.message || 'Comparison failed, try again.')
      setAppState('error')
    }
  }

  function handleStartCompare() {
    setCompareUrls([results?.website_url || '', ''])
    navigate(comparePath())
  }

  function handleScanFromLeaderboard(url) {
    setInputMode('website')
    markShown('home') // so the route effect doesn't reset the scan we're about to start
    navigate('/')
    runAnalysis({ website: url, github: '' })
  }

  function handleNewAnalysis() {
    setAppState('idle')
    setResults(null)
    setComparison(null)
    setErrorMsg('')
    setValidationError('')
    setInputMode('website')
    setWebsiteUrl('')
    setGithubUrl('')
    setCompareUrls(['', ''])
    markShown('home')
    navigate('/')
  }

  const onCompareRoute = route.name === 'compare'
  const onLeaderboardRoute = route.name === 'leaderboard'
  const loadingDomains = onCompareRoute ? compareUrls : [websiteUrl, githubUrl]

  return (
    <div className="min-h-screen bg-bg-base">
      <Header
        showNewAnalysis={appState === 'done' || route.name !== 'home'}
        onNewAnalysis={handleNewAnalysis}
        onLeaderboard={() => navigate(LEADERBOARD_PATH)}
      />

      <main className="pt-14">
        {appState === 'loading' && (
          <LoadingView urls={loadingMessage ? [] : loadingDomains} message={loadingMessage} />
        )}

        {(appState === 'idle' || appState === 'error') && onCompareRoute && (
          <CompareForm
            urls={compareUrls}
            onUrlsChange={setCompareUrls}
            onSubmit={handleCompare}
            validationError={validationError}
            errorMsg={errorMsg}
          />
        )}

        {appState !== 'loading' && onLeaderboardRoute && (
          <LeaderboardView onScan={handleScanFromLeaderboard} />
        )}

        {(appState === 'idle' || appState === 'error') && !onCompareRoute && !onLeaderboardRoute && (
          <LandingView
            inputMode={inputMode}
            onModeChange={setInputMode}
            websiteUrl={websiteUrl}
            githubUrl={githubUrl}
            onWebsiteChange={setWebsiteUrl}
            onGithubChange={setGithubUrl}
            onSubmit={handleSubmit}
            onCompare={() => navigate(comparePath())}
            onLeaderboard={() => navigate(LEADERBOARD_PATH)}
            loading={false}
            validationError={validationError}
            errorMsg={errorMsg}
          />
        )}

        {appState === 'done' && onCompareRoute && comparison && (
          <CompareView reports={comparison} onOpenReport={(id) => navigate(reportPath(id))} />
        )}

        {appState === 'done' && !onCompareRoute && results && (
          <ResultsView
            results={results}
            onRescan={handleRescan}
            onCompare={handleStartCompare}
            onOpenReport={(id) => navigate(reportPath(id))}
          />
        )}
      </main>
    </div>
  )
}
