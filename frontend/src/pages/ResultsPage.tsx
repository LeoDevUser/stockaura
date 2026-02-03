import { useSearchParams, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Chart from '../components/Chart'
import { PositionSizingCard, ZEMAIndicator } from '../components/Sizing'
import { LiquidityAnalysis } from '../components/LiquidityAnalysis'
import { UnifiedTradingRecommendation, DetailedSignalBreakdown } from '../components/TradingRecommendation'
import '../styles/ResultsPage.css'
import '../styles/Direction.css'
import '../styles/Trend.css'
import '../styles/Hurst.css'
import '../styles/Liquidity.css'
import SearchBar from '../components/SearchBar'
import logo from '../assets/logo-dark.png'
import home from '../assets/home.png'

export interface AnalysisResult {
  ticker: string
  window_days: number
  period: string
  hurst: number | null
  hurst_oos: number | null
  momentum_corr: number | null
  momentum_corr_oos: number | null
  lb_pvalue: number | null
  adf_pvalue: number | null
  mean_rev_up: number | null
  mean_rev_down: number | null
  mean_rev_up_oos: number | null
  mean_rev_down_oos: number | null
  sharpe: number | null
  volatility: number | null
  Return: number | null
  predictability_score: number
  zscore: number | null
  z_ema: number | null
  volatility_category: string | null
  golden_cross_short: boolean | null
  final_signal: string | null
  regime_stability: number | null
  data_points: number
  transaction_cost: number
  slippage: number
  trend_direction: 'UP' | 'DOWN' | 'NEUTRAL' | null
  recent_return_1y: number | null
  recent_return_6m: number | null
  recent_return_3m: number | null
  recent_return_1m: number | null
  title: string
  current: number
  currency: string
  suggested_shares: number | null
  stop_loss_price: number | null
  position_risk_amount: number | null
  // Liquidity fields
  avg_daily_volume: number | null
  amihud_illiquidity: number | null
  liquidity_score: string | null
  position_size_vs_volume: number | null
  estimated_slippage_pct: number | null
  total_friction_pct: number | null
  expected_edge_pct: number | null
  is_liquid_enough: boolean | null
  liquidity_warning: string | null
  OHLC: Array<{
    Date: string
    Open: number
    Close: number
    Low: number
    High: number
  }>
  error?: string
}

interface TradeabilityAssessment {
  tradeable: boolean
  reason: string
  confidence: 'high' | 'medium' | 'low'
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
        console.error('Error fetching results:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchResults()
  }, [ticker])

  // Calculate tradeability assessment
  const assessTradeability = (): TradeabilityAssessment => {
    if (!results) return { tradeable: false, reason: 'No data', confidence: 'high' }

    // Check 1: Out-of-sample stability (most important for model validity)
    if (results.regime_stability !== null && results.regime_stability < 0.6) {
      return {
        tradeable: false,
        reason: 'Pattern unstable out-of-sample (deteriorated in test period)',
        confidence: 'high'
      }
    }

    // Check 2: Predictability strength
    if (results.predictability_score < 2) {
      return {
        tradeable: false,
        reason: 'Weak predictability signal (score < 2)',
        confidence: 'high'
      }
    }

    // Check 3: Pattern hold-up (if we have OOS data)
    if (results.momentum_corr_oos !== null && results.momentum_corr !== null) {
      const corrDegradation = Math.abs(results.momentum_corr - results.momentum_corr_oos)
      if (corrDegradation > 0.15) {
        return {
          tradeable: false,
          reason: 'Momentum correlation degraded significantly out-of-sample',
          confidence: 'high'
        }
      }
    }

    // Check 4: Liquidity assessment (critical liquidity issues only)
    if (results.liquidity_warning !== null && results.liquidity_warning !== undefined) {
      if (results.liquidity_warning.includes('CRITICAL') || 
          results.liquidity_warning.includes('exceeds 5%')) {
        return {
          tradeable: false,
          reason: `Liquidity issue: ${results.liquidity_warning}`,
          confidence: 'high'
        }
      }
    }

    // Check 5: Edge vs Friction (profitability, not just tradeability)
    if (results.expected_edge_pct !== null && results.total_friction_pct !== null) {
      const edgeToFrictionRatio = results.expected_edge_pct / results.total_friction_pct
      
      if (edgeToFrictionRatio < 1.5) {
        return {
          tradeable: false,
          reason: `Edge (${(results.expected_edge_pct).toFixed(3)}%) too small vs costs (${results.total_friction_pct.toFixed(3)}%) - ratio ${edgeToFrictionRatio.toFixed(2)}x (need >3x)`,
          confidence: 'high'
        }
      }
    }

    // If we got this far: pattern shows promise
    if (results.predictability_score >= 3 && 
        results.regime_stability !== null && 
        results.regime_stability > 0.7) {
      return {
        tradeable: true,
        reason: 'Pattern stable and passes basic criteria - requires paper trading to validate edge',
        confidence: 'medium'
      }
    }

    // Marginal case
    if (results.predictability_score >= 2) {
      return {
        tradeable: true,
        reason: 'Pattern shows some promise but weak signals - high risk of false positives',
        confidence: 'low'
      }
    }

    return {
      tradeable: false,
      reason: 'Insufficient evidence of stable edge',
      confidence: 'medium'
    }
  }

  // Determine market regime description
  const getRegimeDescription = (): string => {
    if (!results?.hurst) return 'Unknown'
    if (results.hurst > 0.55) return 'Trending'
    if (results.hurst < 0.45) return 'Mean-Reverting'
    return 'Random Walk'
  }

  const tradeability = assessTradeability()

  if (loading) return <div className="loading-page"><p>Loading...</p></div>

  if (results?.error) return (
    <div className="delisted-container" onClick={() => navigate('/')}>
      <p className='delisted-error'>{results.error}</p>
      <img src={home} alt='Landing' />
      <p className='delisted-go-back'>Go Back to Landing Page</p>
    </div>
  )

  if (!results) return <div className="no-results"><p>No results</p></div>

  return (
    <div className="results-page">
      {/* Navigation Header */}
      <div className='nav'>
        <div className='logo-dark'>
          <img src={logo} alt='Dark Logo' onClick={() => navigate('/')} />
        </div>
        <div className="ticker-info">
          <h1>{results.title || 'Undefined'}</h1>
          <h2>Ticker: {ticker}&emsp;&emsp;{results.current} {results.currency}</h2>
        </div>
        <div className='home-search'>
          <div className='search-section-landing'>
            <SearchBar
              onSelect={handleNavigate}
              placeholder='Enter a stock ticker to analyze it..'
            />
          </div>
          <div className='home'>
            <img src={home} alt='Landing' onClick={() => navigate('/')} />
          </div>
        </div>
      </div>

      {/* Main Results Grid */}
      <div className="results-grid">
        
        {/* LEFT SECTION: Header Stats */}
        <div className="section header-stats">
          <h3>Header Stats</h3>
          
          {results.trend_direction && (
            <div className="stat trend-stat">
              <label>Current Trend (1-Year)</label>
              <div className={`trend-value trend-${results.trend_direction.toLowerCase()}`}>
                {results.trend_direction === 'UP' && '📈 UP'}
                {results.trend_direction === 'DOWN' && '📉 DOWN'}
                {results.trend_direction === 'NEUTRAL' && '➡️ NEUTRAL'}
              </div>
              {results.recent_return_1y && (
                <small>{(results.recent_return_1y * 100).toFixed(2)}% (1-year return)</small>
              )}
            </div>
          )}

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

          {results.regime_stability !== null && (
            <div className="stat">
              <label>Regime Stability (OOS)</label>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${results.regime_stability * 100}%`,
                    backgroundColor: results.regime_stability > 0.7 ? '#22c55e' : results.regime_stability > 0.6 ? '#f59e0b' : '#ef4444'
                  }}
                />
              </div>
              <small>{(results.regime_stability * 100).toFixed(0)}%</small>
            </div>
          )}

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
              <div className={`value ${results.Return < 0 ? 'negative' : 'positive'}`}>
                {results.Return.toFixed(2)}%
              </div>
            </div>
          )}
        </div>

        {/* MIDDLE SECTION: Statistical Engine */}
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
                <div className="hurst-value">In-Sample: {results.hurst.toFixed(3)}</div>
                {results.hurst_oos !== null && (
                  <div className="hurst-value-oos">Out-Sample: {results.hurst_oos.toFixed(3)}</div>
                )}
              </div>
            )}
          </div>

          {results.adf_pvalue !== null && (
            <div className="metric-box">
              <label>ADF Test: </label>
              <br/>
              <div className={`status ${results.adf_pvalue < 0.05 ? 'stationary' : 'non-stationary'}`}>
                {results.adf_pvalue < 0.05 ? '✓ Stationary' : '✗ Non-Stationary'}
              </div>
              <br/>
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

        {/* RIGHT SECTION: Chart & Summary */}
        <div className="section visual-summary">
          <Chart ohlcData={results.OHLC} ticker={ticker || 'Unknown'} />

          {/* Tradeability Assessment */}
          <div className={`tradeability-box ${tradeability.tradeable ? 'tradeable' : 'not-tradeable'}`}>
            <h4>{tradeability.tradeable ? '✓ POTENTIALLY TRADEABLE' : '✗ NOT RECOMMENDED'}</h4>
            <p><strong>Assessment:</strong> {tradeability.reason}</p>
            <p style={{ fontSize: '0.85em', color: '#aaa' }}>
              Confidence: <span style={{ textTransform: 'capitalize' }}>{tradeability.confidence}</span>
            </p>
          </div>

          {/* Summary Text */}
          <div className="summary-text">
            {results.hurst !== null && (
              <p>
                <strong>{ticker}</strong> is in a <span className={getRegimeDescription().toLowerCase()}>
                  {getRegimeDescription()}
                </span> regime with {results.adf_pvalue && results.adf_pvalue < 0.05 ? 'stationary' : 'non-stationary'} price action.
                {results.trend_direction && (
                  <> Currently in a <strong>{results.trend_direction} trend</strong>.</>
                )}
              </p>
            )}

            {results.Return && results.Return < -20 && (
              <p style={{ fontSize: '0.85em', color: '#ef4444', marginTop: '1em', fontWeight: 'bold' }}>
                ⚠⚠⚠ SEVERE WARNING: This stock has lost {Math.abs(results.Return).toFixed(1)}% annually. Consider bankruptcy risk before trading.
              </p>
            )}

            <p style={{ fontSize: '0.85em', color: '#888', marginTop: '1em' }}>
              ⚠ <strong>Important:</strong> Historical patterns don't guarantee future performance. 
              Even if tradeable, paper trade first to verify the strategy works in real conditions.
            </p>
          </div>
        </div>
      </div>

      {/* UNIFIED TRADING RECOMMENDATION */}
      <div className="recommendation-section">
        <UnifiedTradingRecommendation results={results} />
      </div>

      {/* OPTIONAL: Detailed Signal Breakdown for Power Users */}
      <div className="detailed-section">
        <DetailedSignalBreakdown results={results} />
      </div>

      {/* DETAILED METRICS SECTION */}
      <div className="additional-metrics">
        <h3>Detailed Metrics</h3>
        
        <div className="metrics-grid">
          {results.momentum_corr !== null && (
            <div className="metric-card">
              <label>Momentum Correlation</label>
              <div className="value">{results.momentum_corr.toFixed(3)}</div>
              {results.momentum_corr_oos !== null && (
                <div className="value-secondary">
                  Out-of-Sample: {results.momentum_corr_oos.toFixed(3)}
                  {Math.abs(results.momentum_corr - results.momentum_corr_oos) > 0.1 && (
                    <span style={{ color: '#ef4444' }}> ⚠ Degraded</span>
                  )}
                </div>
              )}
            </div>
          )}

          {results.mean_rev_up !== null && (
            <div className="metric-card">
              <label>Mean Rev After Up Move</label>
              <div className="value">{(results.mean_rev_up * 100).toFixed(2)}%</div>
              {results.mean_rev_up_oos !== null && (
                <div className="value-secondary">
                  Out-of-Sample: {(results.mean_rev_up_oos * 100).toFixed(2)}%
                </div>
              )}
            </div>
          )}

          {results.mean_rev_down !== null && (
            <div className="metric-card">
              <label>Mean Rev After Down Move</label>
              <div className="value">{(results.mean_rev_down * 100).toFixed(2)}%</div>
              {results.mean_rev_down_oos !== null && (
                <div className="value-secondary">
                  Out-of-Sample: {(results.mean_rev_down_oos * 100).toFixed(2)}%
                </div>
              )}
            </div>
          )}

          {results.zscore !== null && (
            <div className="metric-card">
              <label>Current Z-Score</label>
              <div className="value">{results.zscore.toFixed(3)}</div>
              <small>
                {Math.abs(results.zscore) > 2 
                  ? '⚠ Extreme' 
                  : Math.abs(results.zscore) > 1 
                  ? 'Moderate' 
                  : 'Normal'}
              </small>
            </div>
          )}
        </div>

        {/* Position Sizing Card */}
        <div className='sizing-container'>
          <PositionSizingCard results={results}></PositionSizingCard>
        </div>

        {/* Z-EMA Indicator */}
        <div className='zema-container'>
          <ZEMAIndicator results={results}></ZEMAIndicator>
        </div>

        {/* Liquidity Analysis */}
        <div className='liquidity-container'>
          <LiquidityAnalysis results={results}></LiquidityAnalysis>
        </div>
      </div>
    </div>
  )
}
