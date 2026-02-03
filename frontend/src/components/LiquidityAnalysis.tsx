import { type AnalysisResult } from '../pages/ResultsPage.tsx'
import '../styles/Liquidity.css'

export function LiquidityAnalysis({ results }: { results: AnalysisResult }) {
  if (!results.liquidity_score) return null

  return (
    <div className="liquidity-analysis-box">
      <h4>💧 Liquidity & Friction Analysis</h4>

      {/* Main Liquidity Score */}
      <div className="liquidity-score-card">
        <div className={`liquidity-badge ${results.liquidity_score.toLowerCase()}`}>
          {results.liquidity_score === 'HIGH' && '✓ HIGH LIQUIDITY'}
          {results.liquidity_score === 'MEDIUM' && '⚠ MEDIUM LIQUIDITY'}
          {results.liquidity_score === 'LOW' && '✗ LOW LIQUIDITY'}
        </div>
        
        {results.liquidity_warning && (
          <div className="liquidity-warning">
            <strong>⚠ Warning:</strong>
            <p>{results.liquidity_warning}</p>
          </div>
        )}
      </div>

      {/* Volume Analysis */}
      <div className="friction-metrics">
        <div className="metric-row">
          <span className="metric-label">30-Day Avg Volume</span>
          <span className="metric-value">
            {results.avg_daily_volume?.toLocaleString()}
          </span>
        </div>

        <div className="metric-row">
          <span className="metric-label">Suggested Position</span>
          <span className="metric-value">
            {results.suggested_shares?.toLocaleString()} shares
          </span>
        </div>

        <div className={`metric-row ${(results.position_size_vs_volume || 0) > 0.02 ? 'warning' : ''}`}>
          <span className="metric-label">Position as % of Volume</span>
          <span className="metric-value">
            {((results.position_size_vs_volume || 0) * 100).toFixed(2)}%
          </span>
          {(results.position_size_vs_volume || 0) > 0.01 && (
            <span className="metric-warning">⚠  {">"} 1% = HIGH SLIPPAGE</span>
          )}
          {(results.position_size_vs_volume || 0) > 0.05 && (
            <span className="metric-warning">❌ {">"} 5% = NOT EXECUTABLE</span>
          )}
        </div>
      </div>

      {/* Liquidity Metrics */}
      <div className="liquidity-metrics">
        <div className="metric-row">
          <span className="metric-label">Amihud Illiquidity Ratio</span>
          <span className="metric-value">
            {results.amihud_illiquidity?.toFixed(6)}
          </span>
          <span className="metric-hint">
            {results.amihud_illiquidity && results.amihud_illiquidity < 0.001 && '(Highly liquid)'}
            {results.amihud_illiquidity && results.amihud_illiquidity >= 0.001 && results.amihud_illiquidity < 0.01 && '(Moderate liquidity)'}
            {results.amihud_illiquidity && results.amihud_illiquidity >= 0.01 && '(Illiquid)'}
          </span>
        </div>
      </div>

      {/* Friction Cost Breakdown */}
      <div className="friction-cost-box">
        <h5>Friction Cost Breakdown (Round Trip)</h5>
        
        <div className="cost-breakdown">
          <div className="cost-item">
            <span className="cost-label">Estimated Slippage</span>
            <span className="cost-value">{results.estimated_slippage_pct?.toFixed(3)}%</span>
            <span className="cost-hint">Price movement + spread</span>
          </div>

          <div className="cost-item">
            <span className="cost-label">Transaction Cost (2x)</span>
            <span className="cost-value">{((results.transaction_cost || 0.001) * 200).toFixed(3)}%</span>
            <span className="cost-hint">In + Out (2 trades)</span>
          </div>

          <div className="cost-item total">
            <span className="cost-label">
              <strong>Total Friction</strong>
            </span>
            <span className="cost-value-total">
              {results.total_friction_pct?.toFixed(3)}%
            </span>
          </div>
        </div>
      </div>

      {/* Edge vs Friction */}
      <div className={`edge-vs-friction ${results.expected_edge_pct && results.total_friction_pct && results.expected_edge_pct > (results.total_friction_pct * 3) ? 'profitable' : 'unprofitable'}`}>
        <h5>Statistical Edge vs Costs</h5>
        
        <div className="edge-comparison">
          <div className="edge-item">
            <span className="edge-label">Expected Edge (Annual)</span>
            <span className="edge-value">{results.expected_edge_pct?.toFixed(3)}%</span>
          </div>

          <div className="edge-item">
            <span className="edge-label">Total Friction per Trade</span>
            <span className="edge-value">{results.total_friction_pct?.toFixed(3)}%</span>
          </div>

          <div className="edge-ratio">
            <span className="ratio-label">Edge / Friction Ratio</span>
			<span className="ratio-value">
			  {results.expected_edge_pct && results.total_friction_pct && results.total_friction_pct !== 0
				? (results.expected_edge_pct / results.total_friction_pct).toFixed(1)
				: "0.0"}x
			</span>
            {results.expected_edge_pct && results.total_friction_pct && (
              <span className="ratio-hint">
                {results.expected_edge_pct / results.total_friction_pct > 3
                  ? '✓ Edge covers costs (>3x)'
                  : '✗ Edge too small vs costs (<3x)'}
              </span>
            )}
          </div>
        </div>

        <div className="edge-conclusion">
          {results.expected_edge_pct && results.total_friction_pct && results.expected_edge_pct > (results.total_friction_pct * 3) ? (
            <p style={{ color: '#22c55e' }}>
              ✓ <strong>Edge is sufficient</strong> — costs are covered by statistical edge (before slippage on entry/exit)
            </p>
          ) : (
            <p style={{ color: '#ef4444' }}>
              ✗ <strong>Edge is insufficient</strong> — costs exceed statistical edge. This strategy would likely lose money after friction.
            </p>
          )}
        </div>
      </div>

      {/* Final Liquidity Verdict */}
      <div className="liquidity-verdict">
        <h5>Can This Stock Be Traded?</h5>
        {results.is_liquid_enough ? (
          <div className="verdict-good">
            ✓ <strong>YES</strong> — Stock meets liquidity requirements
            <p>Position size is reasonable and edge covers friction costs</p>
          </div>
        ) : (
          <div className="verdict-bad">
            ✗ <strong>NO</strong> — Stock fails liquidity or cost-benefit test
            <p>Consider a different stock or reduce position size</p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * UserSettings Component (Optional but recommended)
 * Allows users to input their own commission and adjust friction calculations
 */
export function FrictionSettings({ 
  onCommissionChange 
}: { 
  onCommissionChange: (commission: number) => void 
}) {
  const [commission, setCommission] = React.useState(0.001)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value) / 100 // Convert from % to decimal
    setCommission(value)
    onCommissionChange(value)
  }

  return (
    <div className="friction-settings">
      <label>
        <span>Transaction Commission (%)</span>
        <input
          type="number"
          value={(commission * 100).toFixed(3)}
          onChange={handleChange}
          step={0.001}
          min={0}
        />
      </label>
      <small>
        Typical commissions: Schwab $0 | IB $0.5% | Crypto 0.1%
      </small>
    </div>
  )
}
