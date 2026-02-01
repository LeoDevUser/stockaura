import { useSearchParams, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Chart from '../components/Chart'
import '../styles/ResultsPage.css'
import SearchBar from '../components/SearchBar'
import logo from '../assets/logo-dark.png'
import home from '../assets/home.png'

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
  title: string
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
  const [results, setResults] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const navigate = useNavigate()

  const handleNavigate = (ticker: string) => {
    navigate(`/results?ticker=${ticker}`)
  }

  useEffect(() => {
    const fetchResults = async () => {
      if (!ticker) return
      try {
        setLoading(true)
        const response = await fetch(`/api/analyze?ticker=${ticker}&period=5y&window_days=5`)
        const data: AnalysisResult = await response.json()
        setResults(data)
      } catch (err) {
      } finally {
        setLoading(false)
      }
    }
    fetchResults()
  }, [ticker])

  if (loading) return <div className="loading-page"><p>Loading...</p></div>
  if (results?.error) return (
	<div className="delisted-container"onClick={() => navigate('/')}>
		<p className='delisted-error'>{results.error}</p>
		<img src={home} alt='Landing'/>
		<p className='delisted-go-back'>Go Back to Landing Page</p>
	</div>
  )
  if (!results) return <div className="results-container"><p>No results</p></div>
	  console.log(results)

  return (
    <div className="results-page">
	<div className='nav'>
	  <div className='logo-dark'>
		  <img src={logo} alt='Dark Logo' onClick={() => navigate('/')}/>
	  </div>
        <div className="ticker-info">
          <h1>{results.title || 'Undefined'}</h1>
		  <h2>Ticker: {ticker}</h2>
        </div>
		<div className='home-search'>
	  <div className='search-section-landing'>
	  <SearchBar
	  onSelect={handleNavigate}
	  placeholder='Enter a stock ticker to analyze it..'/>
		</div>
		<div className='home'>
		<img src={home} alt='Landing' onClick={() => navigate('/')} />
		</div>
		</div>
	</div>
      <div className="results-grid">
        {/* Left Section - Header Stats */}
        <div className="section header-stats">
          <h3>Header Stats</h3>
          <div className="stat">
            <label>Predictability Score</label>
            <div className="score">{results.predictability_score}/4</div>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${(results.predictability_score / 4) * 100}%` }}
              />
            </div>
          </div>
          {results.sharpe !== null && (
            <div className="stat">
              <label>Sharpe Ratio</label>
              <div className="value">{results.sharpe.toFixed(2)}</div>
            </div>
          )}
          {results.volatility !== null && (
            <div className="stat">
              <label>Volatility (Annual)</label>
              <div className="value">{results.volatility.toFixed(2)}%</div>
            </div>
          )}
          {results.Return !== null && (
            <div className="stat">
              <label>Return (Annual)</label>
              <div className="value">{results.Return.toFixed(2)}%</div>
            </div>
          )}
        </div>

        {/* Middle Section - Statistical Engine */}
        <div className="section statistical-engine">
          <h3>Statistical Engine</h3>
          
          <div className="metric-box">
            <label>Market Regime</label>
            {results.hurst !== null && (
              <div className="gauge-container">
                <div className="gauge">
                  <div className="gauge-fill" style={{ 
                    background: results.hurst > 0.55 ? '#ef4444' : results.hurst < 0.45 ? '#22c55e' : '#f59e0b',
                    width: `${Math.max(0, Math.min(100, (results.hurst - 0.3) * 200))}%`
                  }} />
                </div>
                <div className="gauge-labels">
                  <span>Mean Revert</span>
                  <span className="center">Neutral</span>
                  <span>Trending</span>
                </div>
                <div className="hurst-value">Hurst: {results.hurst.toFixed(3)}</div>
              </div>
            )}
          </div>

          {results.adf_pvalue !== null && (
            <div className="metric-box">
              <label>ADF Test: Stationarity</label>
              <div className={`status ${results.adf_pvalue < 0.05 ? 'stationary' : 'non-stationary'}`}>
                {results.adf_pvalue < 0.05 ? '✓ Stationary' : '✗ Non-Stationary'}
              </div>
              <small>p-value: {results.adf_pvalue.toFixed(4)}</small>
            </div>
          )}

          {results.lb_pvalue !== null && (
            <div className="metric-box">
              <label>Ljung-Box Test</label>
              <div className={`status ${results.lb_pvalue < 0.05 ? 'significant' : 'insignificant'}`}>
                {results.lb_pvalue < 0.05 ? '✓ Autocorrelated' : '✗ No Autocorrelation'}
              </div>
              <small>p-value: {results.lb_pvalue.toFixed(4)}</small>
            </div>
          )}
        </div>

        {/* Right Section - Chart & Summary */}
        <div className="section visual-summary">
          <Chart ohlcData={results.OHLC} ticker={ticker || 'Unknown'} />
          
          <div className="summary-text">
            <p>
              Based on the Hurst, ADF and LB models, <strong>{ticker}</strong> is currently in a{' '}
              <span className={results.hurst! > 0.55 ? 'trending' : results.hurst! < 0.45 ? 'mean-reverting' : 'neutral'}>
                {results.hurst! > 0.55 ? 'strong trending' : results.hurst! < 0.45 ? 'mean-reverting' : 'neutral'}
              </span>{' '}
              regime with {results.adf_pvalue! < 0.05 ? 'low' : 'high'}-stationarity, indicating{' '}
              {results.predictability_score > 2 ? 'strong bullish momentum' : 'weak signals'}.
            </p>
          </div>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="additional-metrics">
        <h3>Additional Metrics</h3>
        <div className="metrics-grid">
          {results.momentum_corr !== null && (
            <div className="metric-card">
              <label>Momentum Correlation</label>
              <div className="value">{results.momentum_corr.toFixed(3)}</div>
            </div>
          )}
          {results.mean_rev_up !== null && (
            <div className="metric-card">
              <label>Mean Rev (Up)</label>
              <div className="value">{(results.mean_rev_up * 100).toFixed(2)}%</div>
            </div>
          )}
          {results.mean_rev_down !== null && (
            <div className="metric-card">
              <label>Mean Rev (Down)</label>
              <div className="value">{(results.mean_rev_down * 100).toFixed(2)}%</div>
            </div>
          )}
          {results.zscore !== null && (
            <div className="metric-card">
              <label>Z-Score</label>
              <div className="value">{results.zscore.toFixed(3)}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
