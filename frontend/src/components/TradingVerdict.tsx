import { type AnalysisResult } from '../pages/ResultsPage.tsx'
import '../styles/TradingVerdict.css'

interface TradingVerdictProps {
  results: AnalysisResult
  transactionCost: number
  accountSize: number
}

export function TradingVerdict({ results, transactionCost, accountSize }: TradingVerdictProps) {
  if (!results.final_signal) return null

  // Recalculate friction with user's transaction cost
  const dynamicSlippage = results.estimated_slippage_pct ? results.estimated_slippage_pct / 100 : 0.0005
  const totalFriction = (dynamicSlippage + transactionCost) * 2
  const totalFrictionPct = totalFriction * 100

  // Recalculate edge vs friction
  const expectedEdge = results.expected_edge_pct || 0
  const edgeRatio = totalFrictionPct > 0 ? expectedEdge / totalFrictionPct : 0
  const edgeCoversCosts = edgeRatio > 3

  // Signal configurations
  const signalConfig: Record<string, {
    verdict: string
    action: string
    color: string
    riskLevel: string
    confidence: string
    summary: string
  }> = {
    'BUY_UPTREND': {
      verdict: 'TRADEABLE',
      action: '✓ BUY - Uptrend Continuing',
      color: '#22c55e',
      riskLevel: 'MEDIUM',
      confidence: 'HIGH',
      summary: 'Strong uptrend with positive momentum and ideal entry level'
    },
    'BUY_PULLBACK': {
      verdict: 'TRADEABLE',
      action: '✓ BUY - Pullback Entry',
      color: '#22c55e',
      riskLevel: 'MEDIUM',
      confidence: 'HIGH',
      summary: 'Strong uptrend with pullback dip - excellent entry point'
    },
    'BUY_MOMENTUM': {
      verdict: 'TRADEABLE',
      action: '✓ BUY - Momentum Play',
      color: '#22c55e',
      riskLevel: 'MEDIUM-HIGH',
      confidence: 'MEDIUM',
      summary: 'Positive momentum detected in uptrend'
    },
    'SHORT_DOWNTREND': {
      verdict: 'TRADEABLE',
      action: '✓ SHORT - Downtrend Continuing',
      color: '#ef4444',
      riskLevel: 'HIGH',
      confidence: 'HIGH',
      summary: 'Strong downtrend with persistent momentum and ideal entry level'
    },
    'SHORT_BOUNCES_ONLY': {
      verdict: 'TRADEABLE',
      action: '📉 SHORT - Bounces Only',
      color: '#ef4444',
      riskLevel: 'HIGH',
      confidence: 'MEDIUM',
      summary: 'Downtrend detected - only short bounces, avoid holding'
    },
    'SHORT_MOMENTUM': {
      verdict: 'TRADEABLE',
      action: '✓ SHORT - Momentum Play',
      color: '#ef4444',
      riskLevel: 'HIGH',
      confidence: 'MEDIUM',
      summary: 'Downtrend momentum detected'
    },
    'WAIT_PULLBACK': {
      verdict: 'WAIT',
      action: '⏸ WAIT - Pullback Expected',
      color: '#f59e0b',
      riskLevel: 'MEDIUM',
      confidence: 'MEDIUM',
      summary: 'Stock overbought (Z-EMA > 1.0) - wait for pullback before buying'
    },
    'WAIT_SHORT_BOUNCE': {
      verdict: 'WAIT',
      action: '⏸ WAIT - Bounce Expected',
      color: '#f59e0b',
      riskLevel: 'MEDIUM',
      confidence: 'MEDIUM',
      summary: 'Stock oversold (Z-EMA < -1.0) - wait for bounce to short'
    },
    'WAIT_OR_SHORT_BOUNCE': {
      verdict: 'WAIT',
      action: '⚠ WAIT or SHORT Bounce',
      color: '#f59e0b',
      riskLevel: 'MEDIUM-HIGH',
      confidence: 'MEDIUM',
      summary: 'Uptrend showing weakness - wait for breakdown or short the bounce'
    },
    'WAIT_FOR_REVERSAL': {
      verdict: 'WAIT',
      action: '⏸ WAIT - Reversal Possible',
      color: '#f59e0b',
      riskLevel: 'MEDIUM',
      confidence: 'MEDIUM',
      summary: 'Downtrend momentum weakening - wait for reversal confirmation'
    },
    'WAIT_FOR_TREND': {
      verdict: 'WAIT',
      action: '⏸ WAIT - No Clear Trend',
      color: '#f59e0b',
      riskLevel: 'HIGH',
      confidence: 'LOW',
      summary: 'Strong momentum but no clear trend yet - wait for trend confirmation'
    },
    'NO_CLEAR_SIGNAL': {
      verdict: 'DO NOT TRADE',
      action: '⚪ NO CLEAR SIGNAL',
      color: '#888',
      riskLevel: 'N/A',
      confidence: 'LOW',
      summary: 'Insufficient evidence for trade - momentum too weak'
    },
    'DO_NOT_TRADE': {
      verdict: 'DO NOT TRADE',
      action: '❌ DO NOT TRADE',
      color: '#ef4444',
      riskLevel: 'CRITICAL',
      confidence: 'HIGH',
      summary: 'Pattern is unreliable or unstable - avoid trading'
    }
  }

  const config = signalConfig[results.final_signal] || {
    verdict: 'UNKNOWN',
    action: results.final_signal,
    color: '#888',
    riskLevel: 'UNKNOWN',
    confidence: 'UNKNOWN',
    summary: 'Unknown signal'
  }

  // Determine why it failed
  const failureReasons = []
  if (results.predictability_score < 3) {
    failureReasons.push({
      metric: 'Predictability Score',
      value: `${results.predictability_score}/4 (need ≥3)`,
      detail: 'Insufficient statistical tests passed'
    })
  }
  if (results.regime_stability !== null && results.regime_stability < 0.7) {
    failureReasons.push({
      metric: 'Regime Stability',
      value: `${(results.regime_stability * 100).toFixed(0)}% (need ≥70%)`,
      detail: 'Pattern degrades significantly out-of-sample'
    })
  }
  if (!edgeCoversCosts) {
    failureReasons.push({
      metric: 'Edge vs Friction',
      value: `${edgeRatio.toFixed(1)}x (need >3x)`,
      detail: 'Statistical edge too small to cover trading costs'
    })
  }
  if (results.momentum_corr !== null && Math.abs(results.momentum_corr) <= 0.1) {
    failureReasons.push({
      metric: 'Momentum',
      value: `${(results.momentum_corr * 100).toFixed(1)}% (need >10%)`,
      detail: 'No detectable momentum pattern'
    })
  }

  const hasFailed = config.verdict === 'DO NOT TRADE'

  return (
    <div className="trading-verdict-container">
      <h2 className="verdict-title">📊 Trading Verdict</h2>

      {/* Main Verdict Box */}
      <div 
        className={`verdict-main ${config.verdict.toLowerCase().replace(/ /g, '-')}`}
        style={{ borderLeftColor: config.color }}
      >
        <div className="verdict-header">
          <h3 style={{ color: config.color }}>{config.action}</h3>
          <div className="verdict-badges">
            <span className={`badge risk-${config.riskLevel.toLowerCase().replace('-', '_')}`}>
              Risk: {config.riskLevel}
            </span>
            <span className={`badge conf-${config.confidence.toLowerCase()}`}>
              Confidence: {config.confidence}
            </span>
          </div>
        </div>

        <p className="verdict-summary">{config.summary}</p>

        {/* Show failure reasons if DO NOT TRADE */}
        {hasFailed && failureReasons.length > 0 && (
          <div className="failure-reasons">
            <strong>❌ Failed Validation Checks:</strong>
            <ul>
              {failureReasons.map((reason, idx) => (
                <li key={idx}>
                  <strong>{reason.metric}:</strong> {reason.value}
                  <br />
                  <small>{reason.detail}</small>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Show what passed if it's tradeable */}
        {!hasFailed && (
          <div className="passing-metrics">
            <strong>✓ Validation Passed:</strong>
            <div className="metrics-grid-compact">
              <div className="metric-item">
                <span>Predictability</span>
                <strong style={{ color: '#22c55e' }}>{results.predictability_score}/4</strong>
              </div>
              {results.regime_stability !== null && (
                <div className="metric-item">
                  <span>Regime Stability</span>
                  <strong style={{ color: '#22c55e' }}>{(results.regime_stability * 100).toFixed(0)}%</strong>
                </div>
              )}
              <div className="metric-item">
                <span>Edge/Friction</span>
                <strong style={{ color: '#22c55e' }}>{edgeRatio.toFixed(1)}x</strong>
              </div>
              {results.momentum_corr !== null && (
                <div className="metric-item">
                  <span>Momentum</span>
                  <strong style={{ color: '#22c55e' }}>{(results.momentum_corr * 100).toFixed(1)}%</strong>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Show liquidity warning if position too large for market */}
      {results.liquidity_failed && config.verdict !== 'DO NOT TRADE' && (
        <div className="liquidity-failure-warning">
          <h4 style={{ color: '#f59e0b', margin: '0 0 0.75em 0' }}>
            ⚠ Liquidity Constraint
          </h4>
          <p style={{ color: '#d0d0d0', fontSize: '0.95em', lineHeight: '1.6', margin: '0' }}>
            {results.liquidity_warning}
          </p>
          <p style={{ color: '#999', fontSize: '0.85em', marginTop: '1em', fontStyle: 'italic' }}>
            Note: The trading pattern itself is valid ({config.verdict}). The issue is your position size relative to daily trading volume.
          </p>
        </div>
      )}

      {/* Position Details - Only show if tradeable or wait */}
      {config.verdict !== 'DO NOT TRADE' && (
        <div className="position-details">
          <h4>Position Setup</h4>
          
          {results.suggested_shares ? (
            <>
              <div className="position-grid">
                <div className="position-item">
                  <label>Entry</label>
                  <span className="value">{results.suggested_shares} shares @ ${results.current?.toFixed(2)}</span>
                  <small>Position: ${(results.suggested_shares * (results.current || 0)).toFixed(2)}</small>
                </div>
                <div className="position-item">
                  <label>Stop Loss</label>
                  <span className="value" style={{ color: '#ef4444' }}>
                    ${results.stop_loss_price?.toFixed(2)}
                  </span>
                  <small>
                    Risk: {(Math.abs((results.current || 0) - (results.stop_loss_price || 0)) / (results.current || 1) * 100).toFixed(2)}%
                  </small>
                </div>
                <div className="position-item">
                  <label>Risk Amount</label>
                  <span className="value">${results.position_risk_amount?.toFixed(2)}</span>
                  <small>{(results.risk_per_trade * 100).toFixed(1)}% of ${accountSize.toLocaleString()} account</small>
                </div>
              </div>
              
              {results.position_size_note && (
                <div className="position-note">
                  <p style={{ color: '#f59e0b', fontSize: '0.9em', marginTop: '1em', lineHeight: '1.5' }}>
                    💡 {results.position_size_note}
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="position-warning">
              <p style={{ color: '#ef4444', margin: '1em 0', fontSize: '1.1em' }}>
                <strong>⚠ Cannot Execute Position</strong>
              </p>
              {results.position_size_note && (
                <p style={{ color: '#d0d0d0', fontSize: '0.95em', lineHeight: '1.6', marginTop: '0.75em' }}>
                  {results.position_size_note}
                </p>
              )}
              <p style={{ color: '#999', fontSize: '0.85em', marginTop: '1em', fontStyle: 'italic' }}>
                Note: The trading pattern itself is valid. The issue is your account size relative to this stock's price and your risk tolerance.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Market Context */}
      <div className="market-context">
        <h4>Market Analysis</h4>
        <div className="context-grid">
          <div className="context-item">
            <span className="context-label">Momentum Pattern</span>
            <span className="context-value">
              {results.momentum_corr !== null && results.momentum_corr > 0.1
                ? `Strong positive (${(results.momentum_corr * 100).toFixed(1)}%) — trends CONTINUE`
                : results.momentum_corr !== null && results.momentum_corr < -0.1
                ? `Strong negative (${(results.momentum_corr * 100).toFixed(1)}%) — trends REVERSE`
                : 'Weak momentum — no clear pattern'}
            </span>
          </div>
          <div className="context-item">
            <span className="context-label">Market Regime</span>
            <span className="context-value">
              {results.hurst !== null && results.hurst > 0.55
                ? `TRENDING (Hurst ${results.hurst.toFixed(3)}) — follow trends`
                : results.hurst !== null && results.hurst < 0.45
                ? `MEAN-REVERTING (Hurst ${results.hurst.toFixed(3)}) — fade extremes`
                : `RANDOM WALK (Hurst ${results.hurst?.toFixed(3) || 'N/A'}) — no pattern`}
            </span>
          </div>
          <div className="context-item">
            <span className="context-label">Price Position</span>
            <span className="context-value">
              {results.z_ema !== null && results.z_ema > 1.0
                ? `Overbought (Z-EMA ${results.z_ema.toFixed(2)})`
                : results.z_ema !== null && results.z_ema < -1.0
                ? `Oversold (Z-EMA ${results.z_ema.toFixed(2)})`
                : results.z_ema !== null && results.z_ema > -0.5 && results.z_ema < 1.0
                ? `Sweet spot (Z-EMA ${results.z_ema.toFixed(2)})`
                : `Moderate (Z-EMA ${results.z_ema?.toFixed(2) || 'N/A'})`}
            </span>
          </div>
          <div className="context-item">
            <span className="context-label">Current Trend</span>
            <span className="context-value">
              {results.trend_direction === 'UP' && '📈 UPTREND'}
              {results.trend_direction === 'DOWN' && '📉 DOWNTREND'}
              {results.trend_direction === 'NEUTRAL' && '➡️ NEUTRAL'}
              {results.recent_return_1y !== null && ` (${(results.recent_return_1y * 100).toFixed(1)}% 1Y)`}
            </span>
          </div>
        </div>
      </div>

      {/* Liquidity & Costs */}
      <div className="liquidity-costs">
        <h4>Liquidity & Trading Costs</h4>
        <div className="costs-grid">
          <div className="cost-item">
            <label>Daily Volume</label>
            <span>{results.avg_daily_volume?.toLocaleString() || 'N/A'}</span>
          </div>
          <div className="cost-item">
            <label>Position vs Volume</label>
            <span className={results.position_size_vs_volume && results.position_size_vs_volume > 0.02 ? 'warning' : ''}>
              {((results.position_size_vs_volume || 0) * 100).toFixed(3)}%
            </span>
          </div>
          <div className="cost-item">
            <label>Est. Slippage</label>
            <span>{((dynamicSlippage * 100)).toFixed(3)}%</span>
          </div>
          <div className="cost-item">
            <label>Transaction Cost</label>
            <span>{(transactionCost * 100).toFixed(3)}%</span>
          </div>
          <div className="cost-item total">
            <label>Total Friction (Round Trip)</label>
            <span>{totalFrictionPct.toFixed(3)}%</span>
          </div>
          <div className="cost-item edge">
            <label>Expected Edge (Annual)</label>
            <span>{expectedEdge.toFixed(2)}%</span>
          </div>
          <div className="cost-item ratio">
            <label>Edge / Friction Ratio</label>
            <span style={{ color: edgeCoversCosts ? '#22c55e' : '#ef4444' }}>
              {edgeRatio.toFixed(1)}x {edgeCoversCosts ? '✓' : '✗'}
            </span>
          </div>
        </div>
        
        {results.liquidity_warning && (
          <div className="liquidity-warning">
            ⚠ {results.liquidity_warning}
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="verdict-disclaimer">
        <p>
          <strong>⚠ Important:</strong> Historical patterns don't guarantee future performance. 
          {config.verdict === 'TRADEABLE' && ' Paper trade first to validate the strategy in real conditions.'}
          {config.verdict === 'WAIT' && ' Wait for the specified setup before entering.'}
          {config.verdict === 'DO NOT TRADE' && ' This stock does not meet minimum statistical requirements for reliable trading.'}
        </p>
      </div>
    </div>
  )
}
