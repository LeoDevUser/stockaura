export const tooltipContent = {
  predictabilityScore: (
    <>
      <strong>Predictability Score (0-4)</strong>
      <p>Measures how many statistical tests the stock passes. Each test validates whether the stock has exploitable patterns:</p>
      <ul>
        <li><strong>Ljung-Box Test:</strong> Detects autocorrelation (past prices predict future)</li>
        <li><strong>Hurst Exponent:</strong> Identifies trending vs mean-reverting behavior</li>
        <li><strong>Momentum Correlation:</strong> Measures if price movements continue or reverse</li>
        <li><strong>Mean Reversion:</strong> Tests if extreme moves tend to reverse</li>
      </ul>
      <p><strong>Need ≥3/4 to trade.</strong> Higher score = more reliable patterns.</p>
    </>
  ),

  regimeStability: (
    <>
      <strong>Regime Stability (Out-of-Sample)</strong>
      <p>Measures if the stock's pattern holds up on unseen data (30% test set).</p>
      <p><strong>70%+ required:</strong> Pattern must remain consistent when tested on new data.</p>
      <p>If patterns break down out-of-sample, they're likely random noise, not real edges.</p>
    </>
  ),

  sharpeRatio: (
    <>
      <strong>Sharpe Ratio</strong>
      <p>Risk-adjusted return metric: (Return - Risk-Free Rate) / Volatility</p>
      <ul>
        <li><strong>&lt;0:</strong> Losing money</li>
        <li><strong>0-1:</strong> Poor risk-adjusted returns</li>
        <li><strong>1-2:</strong> Good returns for the risk</li>
        <li><strong>2+:</strong> Excellent risk-adjusted returns</li>
      </ul>
      <p>Higher is better. Compares return to volatility.</p>
    </>
  ),

  volatility: (
    <>
      <strong>Volatility (Annual)</strong>
      <p>Measures price swings (standard deviation of returns, annualized).</p>
      <ul>
        <li><strong>&lt;15%:</strong> Very stable (large-cap stocks)</li>
        <li><strong>15-25%:</strong> Low volatility</li>
        <li><strong>25-35%:</strong> Moderate (typical stocks)</li>
        <li><strong>35-50%:</strong> High volatility</li>
        <li><strong>50%+:</strong> Very high (small-caps, tech)</li>
      </ul>
      <p>Higher volatility = bigger position sizing risk, but potentially larger moves.</p>
    </>
  ),

  annualReturn: (
    <>
      <strong>Return (Annual)</strong>
      <p>Average yearly return based on historical data.</p>
      <p><strong>Important:</strong> Past returns don't guarantee future performance. This is descriptive, not predictive.</p>
      <p>Negative returns indicate long-term decline.</p>
    </>
  ),

  hurstExponent: (
    <>
      <strong>Hurst Exponent</strong>
      <p>Identifies market regime:</p>
      <ul>
        <li><strong>H &lt; 0.45:</strong> Mean-reverting (extremes reverse)</li>
        <li><strong>H = 0.5:</strong> Random walk (no pattern)</li>
        <li><strong>H &gt; 0.55:</strong> Trending (momentum persists)</li>
      </ul>
      <p><strong>In-Sample:</strong> Historical training data</p>
      <p><strong>Out-of-Sample:</strong> Test data (30%)</p>
      <p>Both should agree for reliable regime detection.</p>
    </>
  ),

  adfTest: (
    <>
      <strong>ADF (Augmented Dickey-Fuller) Test</strong>
      <p>Tests if price series is stationary (mean-reverting around a constant mean).</p>
      <ul>
        <li><strong>p &lt; 0.05 (Stationary):</strong> Price tends to revert to mean</li>
        <li><strong>p ≥ 0.05 (Non-Stationary):</strong> Price has no fixed mean (drifts)</li>
      </ul>
      <p>Most stocks are non-stationary (they trend). Stationary stocks may mean-revert.</p>
    </>
  ),

  ljungBox: (
    <>
      <strong>Ljung-Box Test</strong>
      <p>Tests for autocorrelation: Do past returns predict future returns?</p>
      <ul>
        <li><strong>p &lt; 0.05:</strong> Significant autocorrelation (pattern exists)</li>
        <li><strong>p ≥ 0.05:</strong> No autocorrelation (random)</li>
      </ul>
      <p>We want p &lt; 0.05 to confirm exploitable patterns exist.</p>
    </>
  ),

  momentumCorrelation: (
    <>
      <strong>Momentum Correlation</strong>
      <p>Measures if returns continue (positive) or reverse (negative).</p>
      <ul>
        <li><strong>&gt;0.1:</strong> Positive momentum (trends continue)</li>
        <li><strong>&lt;-0.1:</strong> Negative momentum (trends reverse)</li>
        <li><strong>-0.1 to 0.1:</strong> Weak/no pattern</li>
      </ul>
      <p><strong>Need |correlation| &gt; 0.1 to trade.</strong></p>
      <p>In-Sample = training data, Out-of-Sample = test data.</p>
    </>
  ),

  meanReversion: (
    <>
      <strong>Mean Reversion After Large Moves</strong>
      <p>After a large up/down move (top/bottom 25%), what happens next?</p>
      <ul>
        <li><strong>Negative value:</strong> Reverses (mean-reverts)</li>
        <li><strong>Positive value:</strong> Continues (momentum)</li>
        <li><strong>Near zero:</strong> No pattern</li>
      </ul>
      <p>Larger absolute values = stronger pattern.</p>
    </>
  ),

  zScore: (
    <>
      <strong>Current Z-Score (20-day MA)</strong>
      <p>Measures how far current price is from 20-day moving average, in standard deviations.</p>
      <ul>
        <li><strong>&gt;2:</strong> Very overbought</li>
        <li><strong>1-2:</strong> Overbought</li>
        <li><strong>-1 to 1:</strong> Normal range</li>
        <li><strong>-2 to -1:</strong> Oversold</li>
        <li><strong>&lt;-2:</strong> Very oversold</li>
      </ul>
      <p>Extreme values may signal reversals or continuation, depending on regime.</p>
    </>
  ),

  zEMA: (
    <>
      <strong>Z-EMA (Exponential Moving Average)</strong>
      <p>Like Z-Score but uses exponential weighting (more recent prices matter more).</p>
      <ul>
        <li><strong>&gt;1.0:</strong> Overbought - wait for pullback</li>
        <li><strong>-0.5 to 1.0:</strong> Sweet spot for entries</li>
        <li><strong>&lt;-1.0:</strong> Oversold - wait for bounce</li>
      </ul>
      <p>Used for timing entries/exits in trending markets.</p>
    </>
  ),

  dailyVolume: (
    <>
      <strong>Average Daily Volume (30-day)</strong>
      <p>Average number of shares traded per day.</p>
      <p>Higher volume = more liquid (easier to buy/sell without moving price).</p>
      <p><strong>Compare to position size:</strong> Your position should be &lt;2% of daily volume to avoid excessive slippage.</p>
    </>
  ),

  amihudIlliquidity: (
    <>
      <strong>Amihud Illiquidity Ratio</strong>
      <p>Measures price impact per dollar of trading volume: |Return| / (Volume × Price)</p>
      <ul>
        <li><strong>&lt;0.001:</strong> Highly liquid (large-cap)</li>
        <li><strong>0.001-0.01:</strong> Moderately liquid</li>
        <li><strong>&gt;0.01:</strong> Illiquid (price moves easily)</li>
      </ul>
      <p>Lower is better for trading large positions.</p>
    </>
  ),

  positionVsVolume: (
    <>
      <strong>Position Size vs Daily Volume</strong>
      <p>Your position as % of average daily trading volume.</p>
      <ul>
        <li><strong>&lt;0.5%:</strong> Negligible market impact</li>
        <li><strong>0.5-2%:</strong> Acceptable (may have minor slippage)</li>
        <li><strong>&gt;2%:</strong> Too large - will significantly move price</li>
      </ul>
      <p><strong>Keep under 2% to avoid excessive slippage.</strong></p>
    </>
  ),

  slippage: (
    <>
      <strong>Estimated Slippage</strong>
      <p>Expected price degradation when executing your order, based on volatility and spread.</p>
      <p>Formula: 5% of average daily price range</p>
      <p>Higher volatility = wider spreads = more slippage.</p>
    </>
  ),

  transactionCost: (
    <>
      <strong>Transaction Cost</strong>
      <p>Commission/fees charged per trade.</p>
      <ul>
        <li><strong>Interactive Brokers:</strong> ~$0.005/share (0.05%)</li>
        <li><strong>Robinhood/Webull:</strong> $0 (but may have worse execution)</li>
        <li><strong>Traditional brokers:</strong> $5-10/trade (0.1-1%)</li>
      </ul>
      <p><strong>Total friction = (Slippage + Transaction Cost) × 2</strong> (for round trip: entry + exit)</p>
    </>
  ),

  totalFriction: (
    <>
      <strong>Total Friction (Round Trip)</strong>
      <p>Total cost of entering AND exiting a position.</p>
      <p><strong>Formula:</strong> (Slippage + Transaction Cost) × 2</p>
      <p>This is the hurdle your edge must beat. If expected edge &lt; 3× friction, don't trade.</p>
    </>
  ),

  expectedEdge: (
    <>
      <strong>Expected Edge (Annual)</strong>
      <p>Estimated annual profit from exploiting the detected pattern.</p>
      <p><strong>Formula:</strong> |Momentum Correlation| × Volatility</p>
      <ul>
        <li>Stronger correlation = better win rate</li>
        <li>Higher volatility = bigger moves per trade</li>
      </ul>
      <p><strong>Must be &gt;3× Total Friction to trade profitably.</strong></p>
    </>
  ),

  edgeFrictionRatio: (
    <>
      <strong>Edge / Friction Ratio</strong>
      <p>How many times bigger is your edge vs trading costs?</p>
      <ul>
        <li><strong>&lt;3×:</strong> Edge too small - don't trade</li>
        <li><strong>3-5×:</strong> Marginal - proceed with caution</li>
        <li><strong>5-10×:</strong> Good edge over costs</li>
        <li><strong>&gt;10×:</strong> Strong edge</li>
      </ul>
      <p><strong>Requires &gt;3× to pass validation.</strong></p>
    </>
  )
}
