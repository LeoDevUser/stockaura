import { type AnalysisResult } from '../pages/ResultsPage.tsx'
import '../styles/Rec.css'

/**
 * Unified Trading Recommendation
 * Consolidates: Final Signal + Direction + Regime into one clear recommendation
 */
export function UnifiedTradingRecommendation({ results }: { results: AnalysisResult }) {
  if (!results.final_signal) return null

  // Define all possible signals with their details
  const signalDetails = {
    'BUY_UPTREND': {
      action: '✓ BUY - Uptrend Continuing',
      emoji: '📈',
      color: '#22c55e',
      reasoning: [
        '✓ Momentum: Uptrend with positive correlation (0.805)',
        '✓ Regime: TRENDING market (Hurst 0.562) — follow trends',
        '✓ Price: In good zone for entry (Z-EMA -0.671)',
      ],
      riskLevel: 'MEDIUM',
      confidence: 'HIGH'
    },
    'BUY_PULLBACK': {
      action: '✓ BUY - Pullback Entry',
      emoji: '📈',
      color: '#22c55e',
      reasoning: [
        '✓ Momentum: Uptrend with positive correlation (0.805)',
        '✓ Regime: TRENDING market (Hurst 0.562) — follow trends',
        '⚠ Price: Pulled back in uptrend (Z-EMA -0.671) — good entry opportunity',
      ],
      riskLevel: 'MEDIUM',
      confidence: 'HIGH'
    },
    'BUY_MOMENTUM': {
      action: '✓ BUY - Momentum Play',
      emoji: '📈',
      color: '#22c55e',
      reasoning: [
        '✓ Momentum: Positive correlation detected',
        '⚠ Regime: Not in strong trending (Hurst < 0.55)',
        'Follow momentum but with tighter stops',
      ],
      riskLevel: 'MEDIUM-HIGH',
      confidence: 'MEDIUM'
    },
    'SHORT_DOWNTREND': {
      action: '✓ SHORT - Downtrend Continuing',
      emoji: '📉',
      color: '#ef4444',
      reasoning: [
        '✓ Momentum: Downtrend with positive correlation',
        '✓ Regime: TRENDING market (Hurst > 0.55) — follow trends',
        '✓ Price: In good zone for short entry',
      ],
      riskLevel: 'HIGH',
      confidence: 'HIGH'
    },
    'SHORT_BOUNCES_ONLY': {
      action: '📉 SHORT - Bounces Only',
      emoji: '📉',
      color: '#ef4444',
      reasoning: [
        '✓ Momentum: Downtrend persistence',
        '⚠ Regime: Not in strong trending regime',
        '⚠ Strategy: Only short bounces, avoid holding shorts',
      ],
      riskLevel: 'HIGH',
      confidence: 'MEDIUM'
    },
    'WAIT_PULLBACK': {
      action: '⏸ WAIT - Pullback Expected',
      emoji: '⏸',
      color: '#f59e0b',
      reasoning: [
        '✓ Momentum: Uptrend confirmed',
        '✓ Regime: TRENDING market',
        '⚠ Price: Overbought (Z-EMA > 1.0) — wait for pullback before buying',
      ],
      riskLevel: 'MEDIUM',
      confidence: 'MEDIUM'
    },
    'WAIT_SHORT_BOUNCE': {
      action: '⏸ WAIT - Bounce Expected',
      emoji: '⏸',
      color: '#f59e0b',
      reasoning: [
        '✓ Momentum: Downtrend confirmed',
        '✓ Regime: TRENDING market',
        '⚠ Price: Oversold (Z-EMA < -1.0) — wait for bounce to short',
      ],
      riskLevel: 'MEDIUM',
      confidence: 'MEDIUM'
    },
    'WAIT_OR_SHORT_BOUNCE': {
      action: '⚠ WAIT or SHORT Bounce',
      emoji: '⚠',
      color: '#f59e0b',
      reasoning: [
        '✓ Trend: Uptrend but weakening',
        '✗ Momentum: Reversing',
        'Uptrend may be ending — wait for breakdown or short the bounce',
      ],
      riskLevel: 'MEDIUM-HIGH',
      confidence: 'MEDIUM'
    },
    'WAIT_FOR_REVERSAL': {
      action: '⏸ WAIT - Reversal Possible',
      emoji: '⏸',
      color: '#f59e0b',
      reasoning: [
        '✓ Trend: Downtrend but weakening',
        '✗ Momentum: Reversing',
        'Downtrend may be ending — wait for reversal confirmation',
      ],
      riskLevel: 'MEDIUM',
      confidence: 'MEDIUM'
    },
    'WAIT_FOR_TREND': {
      action: '⏸ WAIT - No Clear Trend',
      emoji: '⏸',
      color: '#f59e0b',
      reasoning: [
        '✓ Momentum: Strong signal detected',
        '✗ Trend: No clear direction yet',
        'Wait for trend confirmation before trading',
      ],
      riskLevel: 'HIGH',
      confidence: 'LOW'
    },
    'NO_CLEAR_SIGNAL': {
      action: '⚪ NO CLEAR SIGNAL',
      emoji: '⚪',
      color: '#888',
      reasoning: [
        '✗ Momentum: Too weak to determine pattern',
        '✗ No clear directional bias',
        'Look for other trading opportunities',
      ],
      riskLevel: 'N/A',
      confidence: 'LOW'
    },
    'DO_NOT_TRADE': {
      action: '❌ DO NOT TRADE',
      emoji: '❌',
      color: '#ef4444',
      reasoning: [
        '✗ Pattern is unreliable or unstable',
        '✗ Statistical tests failed',
        'Avoid trading this stock',
      ],
      riskLevel: 'CRITICAL',
      confidence: 'HIGH'
    }
  }

  const signal = signalDetails[results.final_signal] || {
    action: results.final_signal,
    emoji: '❓',
    color: '#888',
    reasoning: ['Unknown signal'],
    riskLevel: 'UNKNOWN',
    confidence: 'UNKNOWN'
  }

  return (
    <div className="unified-recommendation">
      <h3>📊 Trading Recommendation</h3>
      
      {/* Main Signal */}
      <div className="signal-main" style={{ borderLeftColor: signal.color }}>
        <div className="signal-header">
          <span className="signal-emoji">{signal.emoji}</span>
          <span className="signal-action" style={{ color: signal.color }}>
            {signal.action}
          </span>
        </div>
        
        <div className="signal-info">
          <div className="info-item">
            <span className="info-label">Risk Level:</span>
            <span className={`info-value risk-${signal.riskLevel.toLowerCase().replace('-', '_')}`}>
              {signal.riskLevel}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">Confidence:</span>
            <span className={`info-value conf-${signal.confidence.toLowerCase()}`}>
              {signal.confidence}
            </span>
          </div>
        </div>
      </div>

      {/* Three-Part Analysis */}
      <div className="analysis-breakdown">
        <h4>Analysis from 3 Perspectives:</h4>
        
        <div className="perspective">
          <h5>1️⃣ Momentum Pattern</h5>
          <p>
            {results.momentum_corr !== null && results.momentum_corr > 0.1
              ? `Strong positive correlation (${(results.momentum_corr * 100).toFixed(1)}%) — trends tend to CONTINUE`
              : results.momentum_corr !== null && results.momentum_corr < -0.1
              ? `Strong negative correlation (${(results.momentum_corr * 100).toFixed(1)}%) — trends tend to REVERSE`
              : 'Weak momentum pattern — no clear signal'}
          </p>
        </div>

        <div className="perspective">
          <h5>2️⃣ Market Regime</h5>
          <p>
            {results.hurst !== null && results.hurst > 0.55
              ? `TRENDING market (Hurst ${(results.hurst).toFixed(3)}) — follow the trend`
              : results.hurst !== null && results.hurst < 0.45
              ? `MEAN-REVERTING market (Hurst ${(results.hurst).toFixed(3)}) — fade extremes`
              : `RANDOM WALK (Hurst ${(results.hurst).toFixed(3)}) — no clear pattern`}
          </p>
        </div>

        <div className="perspective">
          <h5>3️⃣ Price Position</h5>
          <p>
            {results.z_ema !== null && results.z_ema > 1.0
              ? `Overbought (Z-EMA ${(results.z_ema).toFixed(2)}) — wait for pullback`
              : results.z_ema !== null && results.z_ema < -1.0
              ? `Oversold (Z-EMA ${(results.z_ema).toFixed(2)}) — watch for bounce`
              : results.z_ema !== null && results.z_ema > -0.5 && results.z_ema < 1.0
              ? `Sweet spot (Z-EMA ${(results.z_ema).toFixed(2)}) — good entry zone`
              : `Moderate position (Z-EMA ${(results.z_ema).toFixed(2)})`}
          </p>
        </div>
      </div>

      {/* Why This Signal */}
      <div className="signal-reasoning">
        <h4>Why {signal.action}?</h4>
        <ul>
          {signal.reasoning.map((reason, idx) => (
            <li key={idx}>{reason}</li>
          ))}
        </ul>
      </div>

      {/* Trading Action */}
      <div className="trading-action" style={{ borderLeftColor: signal.color }}>
        <h4>Next Steps:</h4>
        <div className="action-items">
          <div className="action-item">
            <span className="action-title">Entry:</span>
            <span>
              {results.suggested_shares} shares @ ${results.current?.toFixed(2)}
            </span>
          </div>
          <div className="action-item">
            <span className="action-title">Stop Loss:</span>
            <span>
              ${results.stop_loss_price?.toFixed(2)} ({(Math.abs((results.current || 0 - (results.stop_loss_price || 0)) / (results.current || 1)) * 100).toFixed(2)}%)
            </span>
          </div>
          <div className="action-item">
            <span className="action-title">Risk per Trade:</span>
            <span>${results.position_risk_amount?.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Important Disclaimer */}
      <div className="signal-disclaimer">
        <p>
          <strong>⚠ Remember:</strong> Paper trade first to validate the pattern. 
          Past performance does not guarantee future results. This is a statistical pattern, not a guarantee.
        </p>
      </div>
    </div>
  )
}

/**
 * Optional: Detailed Breakdown (for users who want to see all 3 signals side-by-side)
 */
export function DetailedSignalBreakdown({ results }: { results: AnalysisResult }) {
  return (
    <div className="detailed-breakdown">
      <h4>📋 Signal Comparison</h4>
      <p style={{ fontSize: '0.85em', color: '#999', marginBottom: '1em' }}>
        These 3 analyses look at the same stock from different angles. 
        The Final Signal combines all three.
      </p>

      <div className="signal-comparison-grid">
        <div className="comparison-box">
          <h5>Trading Direction</h5>
          <p className="comparison-signal">
            {results.trend_direction === 'UP' && results.momentum_corr && results.momentum_corr > 0.1
              ? '📈 LONG (BUY)'
              : results.trend_direction === 'DOWN' && results.momentum_corr && results.momentum_corr > 0.1
              ? '📉 SHORT (SELL)'
              : '⚪ NEUTRAL'}
          </p>
          <p className="comparison-desc">
            Based on: Trend ({results.trend_direction}) + Momentum ({(results.momentum_corr || 0).toFixed(3)})
          </p>
        </div>

        <div className="comparison-box">
          <h5>Market Regime</h5>
          <p className="comparison-signal">
            {results.hurst !== null && results.hurst > 0.55
              ? '📊 TRENDING'
              : results.hurst !== null && results.hurst < 0.45
              ? '🎯 MEAN-REVERTING'
              : '❓ RANDOM'}
          </p>
          <p className="comparison-desc">
            Based on: Hurst ({(results.hurst || 0).toFixed(3)})
          </p>
        </div>

        <div className="comparison-box">
          <h5>Final Signal</h5>
          <p className="comparison-signal">
            {results.final_signal}
          </p>
          <p className="comparison-desc">
            Combines all factors into one recommendation
          </p>
        </div>
      </div>
    </div>
  )
}
