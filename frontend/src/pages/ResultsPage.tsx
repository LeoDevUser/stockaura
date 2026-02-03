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

  /**
   * CRITICAL FIX: Tradeability Assessment
   * 
   * PRINCIPLE: Single Source of Truth
   * ─────────────────────────────────
   * The backend's generate_trading_signal() performs ALL validation:
   * ✓ Predictability score >= 3
   * ✓ Regime stability >= 0.7
   * ✓ Liquidity adequate (is_liquid_enough)
   * ✓ Momentum detected (|r| > 0.1)
   * ✓ Trend direction clear (UP or DOWN)
   * 
   * The final_signal is the OUTPUT of these checks.
   * 
   * The frontend should TRUST and MAP the signal, NOT re-check metrics.
   */
  const assessTradeability = (): TradeabilityAssessment => {
    if (!results) return { tradeable: false, reason: 'No data', confidence: 'high' }

    const signal = results.final_signal

    // TIER 1: Explicit Rejection
    if (signal === 'DO_NOT_TRADE') {
      return {
        tradeable: false,
        reason: 'Pattern failed statistical validation - insufficient predictability, weak regime stability, or edge too small vs costs',
        confidence: 'high'
      }
    }

    // TIER 2: No Signal
    if (signal === 'NO_CLEAR_SIGNAL') {
      return {
        tradeable: false,
        reason: 'No detectable momentum or market structure too ambiguous',
        confidence: 'high'
      }
    }

    // TIER 3: Wait for Setup (Pattern Good, Entry Not Ready)
    if (signal === 'WAIT_FOR_TREND') {
      return {
        tradeable: true,
        reason: 'Pattern shows merit but trend direction unclear - wait for trend confirmation before entering',
        confidence: 'medium'
      }
    }

    if (signal === 'WAIT_PULLBACK') {
      return {
        tradeable: true,
        reason: 'Uptrend confirmed but price overbought (Z > +1.0) - wait for pullback to better entry',
        confidence: 'high'
      }
    }

    if (signal === 'WAIT_SHORT_BOUNCE') {
      return {
        tradeable: true,
        reason: 'Downtrend confirmed but price oversold (Z < -1.0) - wait for bounce to better short entry',
        confidence: 'high'
      }
    }

    if (signal === 'WAIT_OR_SHORT_BOUNCE') {
      return {
        tradeable: true,
        reason: 'Uptrend weakening with momentum reversing - wait for breakdown or short the bounce',
        confidence: 'medium'
      }
    }

    if (signal === 'WAIT_FOR_REVERSAL') {
      return {
        tradeable: true,
        reason: 'Downtrend weakening with momentum reversing - wait for reversal confirmation',
        confidence: 'medium'
      }
    }

    // TIER 4: Trade Now (Pattern Good + Entry Price Good)
    if (signal === 'BUY_UPTREND') {
      return {
        tradeable: true,
        reason: 'Strong uptrend with positive momentum and ideal entry level - ready to buy',
        confidence: 'high'
      }
    }

    if (signal === 'BUY_PULLBACK') {
      return {
        tradeable: true,
        reason: 'Strong uptrend with pullback dip - excellent entry point for long position',
        confidence: 'high'
      }
    }

    if (signal === 'BUY_MOMENTUM') {
      return {
        tradeable: true,
        reason: 'Positive momentum detected in uptrend - suitable for momentum-following entry',
        confidence: 'medium'
      }
    }

    if (signal === 'SHORT_DOWNTREND') {
      return {
        tradeable: true,
        reason: 'Strong downtrend with persistent momentum and ideal entry level - ready to short',
        confidence: 'high'
      }
    }

    if (signal === 'SHORT_BOUNCES_ONLY') {
      return {
        tradeable: true,
        reason: 'Downtrend detected but not strong trending regime - short bounces only, avoid holding',
        confidence: 'medium'
      }
    }

    if (signal === 'SHORT_MOMENTUM') {
      return {
        tradeable: true,
        reason: 'Negative momentum detected in downtrend - suitable for momentum-following short',
        confidence: 'medium'
      }
    }

    // Fallback (should never reach if signal generation is correct)
    return {
      tradeable: false,
      reason: `Unknown signal: ${signal} - rerun analysis`,
      confidence: 'high'
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

          {/* Tradeability Assessment - NOW USES FINAL_SIGNAL */}
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
