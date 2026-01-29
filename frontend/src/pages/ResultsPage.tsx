import { useSearchParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import '../styles/ResultsPage.css'

interface AnalysisResult {
  ticker: string
  window_days: number
  period: string
  hurst: number | null
  momentum_corr: number | null
  lb_pvalue: number | null
  adf_pvalue: number | null
  mean_rev_up: number | null
  mean_rev_down: number | null
  sharpe: number | null
  volatility: number | null
  Return: number | null
  predictability_score: number
  zscore: number | null
  OHLC: Array<{
    Date: string
    Open: number
    High: number
    Close: number
    Low: number
  }>
  error?: string
}

export default function ResultsPage() {
  const [searchParams] = useSearchParams()
  const ticker = searchParams.get('ticker')
  const title = searchParams.get('title')
  const [results, setResults] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchResults = async () => {
      if (!ticker) return

      try {
        setLoading(true)
        const response = await fetch(`/api/analyze?ticker=${ticker}&period=5y&window_days=5`)
        const data: AnalysisResult = await response.json()
        setResults(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [ticker])

  if (loading) return <div className="results-container"><p>Loading...</p></div>
  if (error) return <div className="results-container"><p>Error: {error}</p></div>
  if (!results) return <div className="results-container"><p>No results</p></div>

  return (
    <div className="results-container">
      <h1>{ticker}</h1>
      <h2>{title || 'Unknown Company'}</h2>
      <pre>{JSON.stringify(results, null, 2)}</pre>
    </div>
  )
}
