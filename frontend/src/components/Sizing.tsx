import { type AnalysisResult } from '../pages/ResultsPage.tsx'
import '../styles/Sizing.css'

export function PositionSizingCard({ results }: { results: AnalysisResult }) {
  if (!results.suggested_shares || !results.stop_loss_price) {
    return null;
  }

  const risk_reward_ratio = results.current ? 
    (results.current - results.stop_loss_price) / Math.abs(results.current - results.stop_loss_price) : 
    0;

  return (
    <div className="position-sizing-box">
      <h4>📊 Position Sizing (Risk-Adjusted)</h4>
      
      <div className="sizing-grid">
        <div className="sizing-item">
          <span className="sizing-label">Entry Price</span>
          <span className="sizing-value">${results.current?.toFixed(2)}</span>
        </div>
        
        <div className="sizing-item">
          <span className="sizing-label">Stop Loss Price</span>
          <span className="sizing-value" style={{ color: '#ef4444' }}>
            ${results.stop_loss_price.toFixed(2)}
          </span>
          <small>
            Risk: {Math.abs((results.current - results.stop_loss_price) / results.current * 100).toFixed(2)}%
          </small>
        </div>
        
        <div className="sizing-item">
          <span className="sizing-label">Suggested Shares</span>
          <span className="sizing-value" style={{ color: '#22c55e' }}>
            {results.suggested_shares}
          </span>
        </div>
        
        <div className="sizing-item">
          <span className="sizing-label">Risk per Trade</span>
          <span className="sizing-value">
            ${results.position_risk_amount?.toFixed(2)}
          </span>
          <small>(2% of $10,000 account)</small>
        </div>
        
        <div className="sizing-item sizing-item-full">
          <span className="sizing-label">Position Value</span>
          <span className="sizing-value">
            ${(results.suggested_shares * (results.current || 0)).toFixed(2)}
          </span>
        </div>
      </div>

      <div className="sizing-note">
        <strong>⚠ How This Was Calculated:</strong>
        <p>
          Based on {results.volatility?.toFixed(1)}% annual volatility ({results.volatility_category}),
          we calculated a {(Math.abs((results.current - results.stop_loss_price) / results.current * 100)).toFixed(2)}% stop loss
          ({((results.current - results.stop_loss_price) / results.current / Math.sqrt(252) * 100 * 2).toFixed(2)}% of 2x daily volatility).
        </p>
      </div>
    </div>
  );
}

// New Component to Display Z-EMA
export function ZEMAIndicator({ results }: { results: AnalysisResult }) {
  if (results.z_ema === null) return null;

  const z_ema = results.z_ema;
  let status = 'Normal';
  let color = '#f59e0b';

  if (z_ema > 2.0) {
    status = 'Highly Overbought';
    color = '#ef4444';
  } else if (z_ema > 1.0) {
    status = 'Overbought';
    color = '#f59e0b';
  } else if (z_ema > -0.5) {
    status = 'Sweet Spot for Long';
    color = '#22c55e';
  } else if (z_ema > -1.5) {
    status = 'Pullback - Good Entry';
    color = '#22c55e';
  } else {
    status = 'Oversold';
    color = '#3b82f6';
  }

  return (
    <div className="zema-box">
      <h4>📈 EMA Z-Score (Recent Price Action)</h4>
      
      <div className="zema-display">
        <div className="zema-value" style={{ color }}>
          {z_ema.toFixed(3)}
        </div>
        <div className="zema-status" style={{ color }}>
          {status}
        </div>
      </div>

      <div className="zema-gauge">
        <div className="gauge-bar">
          <div 
            className="gauge-fill-sizing"
            style={{
              left: `${Math.min(100, Math.max(0, (z_ema + 3) / 6 * 100))}%`,
              backgroundColor: color
            }}
          />
        </div>
        <div className="gauge-labels">
          <span>-3</span>
          <span>0</span>
          <span>+3</span>
        </div>
      </div>

      <div className="zema-explanation">
        <strong>What This Means:</strong>
        <p>
          The EMA Z-score shows how far the current price is from its exponential moving average 
          (weighted toward recent prices). In a trending market:
        </p>
        <ul>
          <li>Z &gt; +2.0: Extremely overextended (risk of pullback)</li>
          <li>Z between 0 and +1: Perfect for buying in uptrend</li>
          <li>Z between -0.5 and 0: Healthy pullback within trend</li>
          <li>Z &lt; -1.5: Major dip (good entry in uptrend)</li>
        </ul>
      </div>
    </div>
  );
}

// New Component for Final Trading Signal
export function FinalTradingSignal({ results }: { results: AnalysisResult }) {
  if (!results.final_signal) return null;

  const signals = {
    'BUY_UPTREND': {
      action: '✓ BUY - Uptrend Continuing',
      color: '#22c55e',
      description: 'Strong uptrend with positive momentum. Enter long position.',
      confidence: 'HIGH'
    },
    'BUY_PULLBACK': {
      action: '✓ BUY - Pullback Entry',
      color: '#22c55e',
      description: 'Stock pulled back in uptrend. Good entry point for long.',
      confidence: 'HIGH'
    },
    'BUY_MOMENTUM': {
      action: '✓ BUY - Momentum Play',
      color: '#22c55e',
      description: 'Positive momentum detected. Consider long position.',
      confidence: 'MEDIUM'
    },
    'SHORT_DOWNTREND': {
      action: '✓ SHORT - Downtrend Continuing',
      color: '#ef4444',
      description: 'Strong downtrend with persistent momentum. Enter short position.',
      confidence: 'HIGH'
    },
    'SHORT_BOUNCES_ONLY': {
      action: '📉 SHORT BOUNCES',
      color: '#ef4444',
      description: 'Stock in downtrend. Short bounces, avoid holding short long-term.',
      confidence: 'MEDIUM'
    },
    'SHORT_MOMENTUM': {
      action: '✓ SHORT - Momentum Play',
      color: '#ef4444',
      description: 'Downtrend momentum detected. Consider short position.',
      confidence: 'MEDIUM'
    },
    'WAIT_PULLBACK': {
      action: '⏸ WAIT - Pullback Expected',
      color: '#f59e0b',
      description: 'Stock overbought (Z > +1). Wait for pullback before buying.',
      confidence: 'MEDIUM'
    },
    'WAIT_SHORT_BOUNCE': {
      action: '⏸ WAIT - Bounce Expected',
      color: '#f59e0b',
      description: 'Stock oversold (Z < -1). Wait for bounce to short.',
      confidence: 'MEDIUM'
    },
    'WAIT_OR_SHORT_BOUNCE': {
      action: '⚠ WAIT or SHORT Bounce',
      color: '#f59e0b',
      description: 'Uptrend showing weakness. Wait for breakdown or short the bounce.',
      confidence: 'MEDIUM'
    },
    'WAIT_FOR_REVERSAL': {
      action: '⏸ WAIT - Reversal Possible',
      color: '#f59e0b',
      description: 'Downtrend momentum weakening. Wait for reversal confirmation.',
      confidence: 'MEDIUM'
    },
    'WAIT_FOR_TREND': {
      action: '⏸ WAIT - No Clear Trend',
      color: '#f59e0b',
      description: 'Strong momentum but no clear trend yet. Wait for trend confirmation.',
      confidence: 'LOW'
    },
    'NO_CLEAR_SIGNAL': {
      action: '⚪ NO CLEAR SIGNAL',
      color: '#888',
      description: 'Insufficient evidence for trade. Look for other opportunities.',
      confidence: 'LOW'
    },
    'DO_NOT_TRADE': {
      action: '❌ DO NOT TRADE',
      color: '#ef4444',
      description: 'Pattern is unreliable or unstable. Avoid trading this stock.',
      confidence: 'HIGH'
    }
  };

  const signal = signals[results.final_signal] || {
    action: results.final_signal,
    color: '#888',
    description: 'Unknown signal',
    confidence: 'UNKNOWN'
  };

  return (
    <div className="final-signal-box" style={{ borderLeftColor: signal.color }}>
      <h4 style={{ color: signal.color }}>{signal.action}</h4>
      <p className="signal-description">{signal.description}</p>
      <p className="signal-confidence">
        Confidence: <strong style={{ color: signal.color }}>{signal.confidence}</strong>
      </p>
    </div>
  );
}
