def interpret(results):
    """interpret statistical results with explicit trading direction based on actual trend"""
    
    ticker = results['ticker']
    window_days = results['window_days']

    print("="*80)
    print(f"{ticker} - STATISTICAL ANALYSIS ({window_days}-Day Window)")
    print("="*80)
    
    # DATA QUALITY CHECK
    print("\n0. DATA QUALITY & STABILITY")
    print("-" * 80)
    if results.get('error'):
        print(f"ERROR: {results['error']}")
        return
    
    print(f"Historical period: {results['period']}")
    print(f"Data points: {results.get('data_points', 'N/A')}")
    
    # Check regime stability
    if results.get('regime_stability') is not None:
        stability = results['regime_stability']
        print(f"Regime stability (train vs test): {stability:.1%}")
        if stability < 0.6:
            print("  ⚠ WARNING: Patterns from training period NOT stable in test period")
        elif stability < 0.8:
            print("  ⚠ CAUTION: Some pattern degradation observed")
        else:
            print("  ✓ Pattern relatively stable across time periods")
    
    # Show trend direction
    trend_direction = results.get('trend_direction')
    if trend_direction:
        print(f"\nCurrent Trend (1-year): {trend_direction}")
        recent_1y = results.get('recent_return_1y')
        if recent_1y:
            print(f"1-year return: {recent_1y*100:.2f}%")
    
    # TEST 1: Autocorrelation
    lb_pvalue = results['lb_pvalue']
    print("\n1. AUTOCORRELATION TEST (Ljung-Box)")
    print("-" * 80)
    print(f"Result: p-value = {lb_pvalue:.4f}")
    if lb_pvalue < 0.05:
        print("✓ Returns ARE autocorrelated (statistically)")
        print("  ⚠ BUT: Correlation strength ≠ tradeable edge (may be arbitraged away)")
    else:
        print("✗ Returns are independent (random walk)")
    
    # TEST 2: ADF
    print("\n2. AUGMENTED DICKEY-FULLER TEST (Stationarity)")
    print("-" * 80)
    adf_pvalue = results.get('adf_pvalue')
    if adf_pvalue:
        print(f"ADF p-value: {adf_pvalue:.4f}")
        if adf_pvalue < 0.05:
            print("✓ Price is stationary (mean-reverting)")
        else:
            print("✗ Price has unit root (random walk)")
    else:
        print("(Insufficient data)")
    
    # TEST 3: Mean Reversion
    print("\n3. MEAN REVERSION ANALYSIS")
    print("-" * 80)
    
    mean_rev_up = results.get('mean_rev_up')
    mean_rev_down = results.get('mean_rev_down')
    
    if mean_rev_up and mean_rev_down:
        print(f"After large UP move (+top 25%): Next {window_days}-day return = {mean_rev_up:.4f} ({mean_rev_up*100:.2f}%)")
        print(f"After large DOWN move (-bottom 25%): Next {window_days}-day return = {mean_rev_down:.4f} ({mean_rev_down*100:.2f}%)")
        
        # Determine mean reversion direction
        if mean_rev_up < -0.005 and mean_rev_down > 0.005:
            print("✓ STRONG mean reversion detected in-sample")
            print("  Direction: SELL after UP moves, BUY after DOWN moves")
        elif mean_rev_up > 0.005 and mean_rev_down < -0.005:
            print("✓ STRONG momentum detected in-sample")
            print("  Direction: BUY after UP moves, SELL after DOWN moves")
        else:
            print("? Weak pattern")
        
        # Out-of-sample test
        mean_rev_up_oos = results.get('mean_rev_up_oos')
        mean_rev_down_oos = results.get('mean_rev_down_oos')
        if mean_rev_up_oos is not None:
            print(f"\n  OUT-OF-SAMPLE (test period):")
            print(f"  After UP move: {mean_rev_up_oos:.4f} ({mean_rev_up_oos*100:.2f}%)")
            print(f"  After DOWN move: {mean_rev_down_oos:.4f} ({mean_rev_down_oos*100:.2f}%)")
            
            # Check if direction is consistent
            in_sample_direction = "UP_PROFITABLE" if mean_rev_up > 0 else "UP_LOSES"
            oos_direction = "UP_PROFITABLE" if mean_rev_up_oos > 0 else "UP_LOSES"
            
            if in_sample_direction != oos_direction:
                print(f"  ⚠ WARNING: Direction CHANGED in out-of-sample period")
            elif abs(mean_rev_up - mean_rev_up_oos) > 0.02 or abs(mean_rev_down - mean_rev_down_oos) > 0.02:
                print(f"  ⚠ WARNING: Pattern DETERIORATED in out-of-sample period")
            else:
                print(f"  ✓ Pattern holds in unseen data")
    else:
        print("(Insufficient data)")
    
    # TEST 4: Momentum Correlation
    momentum_corr = results.get('momentum_corr')
    print("\n4. MOMENTUM ANALYSIS")
    print("-" * 80)
    
    if momentum_corr is not None:
        print(f"Correlation between consecutive {window_days}-day returns: {momentum_corr:.4f}")
        
        if momentum_corr > 0.1:
            print("✓ MOMENTUM detected in-sample")
            print("  (Recent trends tend to continue)")
        elif momentum_corr < -0.1:
            print("✓ MEAN REVERSION detected in-sample")
            print("  (Recent trends tend to reverse)")
        else:
            print("✗ NO clear pattern")
        
        # Out-of-sample
        momentum_corr_oos = results.get('momentum_corr_oos')
        if momentum_corr_oos is not None:
            print(f"\n  OUT-OF-SAMPLE correlation: {momentum_corr_oos:.4f}")
            
            # Check direction consistency
            in_sample_direction = "MOMENTUM" if momentum_corr > 0 else "MEAN_REVERSION"
            oos_direction = "MOMENTUM" if momentum_corr_oos > 0 else "MEAN_REVERSION"
            
            if in_sample_direction != oos_direction:
                print(f"  ⚠ WARNING: Strategy direction REVERSED in out-of-sample period")
                print(f"    In-sample: {in_sample_direction}")
                print(f"    Out-of-sample: {oos_direction}")
            elif abs(momentum_corr - momentum_corr_oos) > 0.1:
                print(f"  ⚠ WARNING: Correlation unstable across periods")
            else:
                print(f"  ✓ Correlation stable")
    else:
        print("(Insufficient data)")
    
    # TEST 5: Hurst
    H = results.get('hurst')
    print("\n5. HURST EXPONENT (Trending vs Mean-Reverting)")
    print("-" * 80)
    
    if H is not None:
        print(f"Hurst Exponent: {H:.4f}")
        
        if H > 0.55:
            print(f"→ TRENDING (H = {H:.2f} > 0.55)")
            print("  Strategy: Follow trends (momentum/trend-following)")
            print("  Direction: Buy on strength, Sell on weakness")
        elif H < 0.45:
            print(f"→ MEAN-REVERTING (H = {H:.2f} < 0.45)")
            print("  Strategy: Fade extremes (mean-reversion)")
            print("  Direction: Buy on weakness, Sell on strength")
        else:
            print(f"→ RANDOM WALK (H = {H:.2f} ≈ 0.5)")
            print("  Strategy: None - no edge")
        
        # Out-of-sample
        H_oos = results.get('hurst_oos')
        if H_oos is not None:
            print(f"\n  OUT-OF-SAMPLE Hurst: {H_oos:.4f}")
            
            # Check direction consistency
            in_sample_regime = "TRENDING" if H > 0.55 else "MEAN_REVERTING" if H < 0.45 else "RANDOM"
            oos_regime = "TRENDING" if H_oos > 0.55 else "MEAN_REVERTING" if H_oos < 0.45 else "RANDOM"
            
            if in_sample_regime != oos_regime:
                print(f"  ⚠ WARNING: Regime TYPE CHANGED in out-of-sample period")
                print(f"    In-sample: {in_sample_regime}")
                print(f"    Out-of-sample: {oos_regime}")
            elif abs(H - H_oos) > 0.1:
                print(f"  ⚠ WARNING: Hurst exponent unstable across periods")
            else:
                print(f"  ✓ Hurst exponent relatively stable")
    else:
        print("(Insufficient data)")
    
    # TEST 6: Sharpe Ratio (with caveats)
    sharpe = results.get('sharpe')
    volatility = results.get('volatility')
    ret = results.get('Return')
    
    print("\n6. SHARPE RATIO (Historical Risk-Adjusted Return)")
    print("-" * 80)
    
    if sharpe and volatility and ret:
        print(f"Sharpe Ratio: {sharpe:.3f}")
        print(f"Volatility (annualized): {volatility:.1f}%")
        print(f"Return (annualized): {ret:.1f}%")
        print("\n  ⚠ IMPORTANT: Past Sharpe ratio does NOT predict future performance")
        print("     (Survivorship bias, regime changes, etc.)")
    else:
        print("(Insufficient data)")
    
    # TRANSACTION COSTS & SLIPPAGE ANALYSIS
    print("\n7. REALISTIC TRADING COSTS")
    print("-" * 80)
    
    transaction_cost = results.get('transaction_cost', 0.001)  # 0.1% per trade
    slippage = results.get('slippage', 0.0005)  # 0.05% slippage
    total_cost_per_round = transaction_cost + slippage
    
    print(f"Estimated transaction cost (per trade): {transaction_cost*100:.2f}%")
    print(f"Estimated slippage: {slippage*100:.2f}%")
    print(f"Total cost per round-trip trade: {total_cost_per_round*100:.2f}%")
    
    # How many trades to recover costs?
    if momentum_corr and abs(momentum_corr) > 0.01:
        expected_edge = abs(momentum_corr) * results.get('volatility', 20) / 100
        if expected_edge > 0:
            trades_to_breakeven = total_cost_per_round / expected_edge
            print(f"\nWith detected edge of ~{expected_edge*100:.2f}%, need ~{trades_to_breakeven:.0f} trades to break even on costs")
            if trades_to_breakeven > 20:
                print("  ⚠ Edge too small relative to costs - strategy likely unprofitable")
    
    # DIRECTION SUMMARY (FIXED - NOW USES ACTUAL TREND)
    print("\n" + "="*80)
    print("TRADING DIRECTION SUMMARY (CORRECTED)")
    print("="*80)
    
    trend_direction = results.get('trend_direction')
    recent_1y = results.get('recent_return_1y')
    
    if momentum_corr is not None:
        print(f"\nMomentum Correlation: {momentum_corr:.3f}")
        
        # CORRECTED LOGIC: Check both momentum AND trend direction
        if momentum_corr > 0.1:
            momentum_type = "MOMENTUM DETECTED (trends continue)"
            
            if trend_direction == "UP":
                direction = "LONG (BUY) BIAS - Uptrend Momentum"
                description = "Price momentum tends to CONTINUE upward"
                action = "✓ Buy on strength, hold while trending up"
            elif trend_direction == "DOWN":
                direction = "SHORT (SELL) BIAS - Downtrend Momentum"
                description = "Price momentum tends to CONTINUE downward"
                action = "✓ Short on weakness, or avoid entirely"
            else:
                direction = "NEUTRAL - Weak Trend"
                description = "Momentum exists but trend unclear"
                action = "⚠ Be cautious, unclear direction"
        
        elif momentum_corr < -0.1:
            momentum_type = "MEAN REVERSION (trends reverse)"
            
            if trend_direction == "UP":
                direction = "SHORT (SELL) BIAS - Buy Weakness"
                description = "Price tends to reverse from extremes"
                action = "✓ Short the highs in uptrend, fade extremes"
            elif trend_direction == "DOWN":
                direction = "LONG (BUY) BIAS - Sell Strength"
                description = "Price tends to bounce from lows"
                action = "✓ Buy the lows in downtrend, fade extremes"
            else:
                direction = "NEUTRAL - Weak Trend"
                description = "Mean reversion exists but trend unclear"
                action = "⚠ Be cautious, unclear direction"
        
        else:
            momentum_type = "NO PATTERN"
            direction = "NO CLEAR BIAS"
            description = "No reliable edge detected"
            action = "✗ Don't trade"
        
        print(f"\nMomentum Type: {momentum_type}")
        print(f"Trend Direction: {trend_direction} ({recent_1y*100:.2f}% in 1 year)" if recent_1y else f"Trend Direction: {trend_direction}")
        print(f"Trading Direction: {direction}")
        print(f"Description: {description}")
        print(f"Action: {action}")
    
    if momentum_corr and momentum_corr > 0.1:
        print("\n✓ TRADING STRATEGY:")
        
        if trend_direction == "UP":
            print("  1. Enter LONG (buy) when: Price shows strength (positive momentum)")
            print("  2. Hold: While momentum continues positive")
            print("  3. Exit: When momentum turns negative")
            print("  4. Risk: If momentum reverses")
        elif trend_direction == "DOWN":
            print("  1. Enter SHORT (sell) when: Price shows weakness (negative momentum)")
            print("  2. Hold: While momentum continues negative")
            print("  3. Exit: When momentum turns positive")
            print("  4. Risk: If stock reverses (unlikely given trend)")
        else:
            print("  WARNING: Cannot determine direction - trend is unclear")
    
    # CONCLUSION
    print("\n" + "="*80)
    print("CONCLUSION: IS THIS TRADEABLE?")
    print("="*80)
    
    predictability_score = results.get('predictability_score', 0)
    
    print(f"\nIn-Sample Predictability Score: {predictability_score}/4")
    if H is not None:
        print(f"  Hurst={H:.2f}, Momentum Corr={momentum_corr:.3f}, LB p={lb_pvalue:.4f}")
    
    print("\n" + "-"*80)
    print("REALISTIC ASSESSMENT:")
    print("-"*80)
    
    if predictability_score >= 3:
        print("\n⚠ STATISTICALLY PREDICTABLE (in-sample)")
        print("  But remember:")
        print("  • In-sample patterns often DON'T repeat out-of-sample")
        print("  • Any edge found is likely small relative to trading costs")
        print("  • If easy to spot, it's probably already arbitraged")
        
        if H and H > 0.55 and momentum_corr and momentum_corr > 0.1:
            if trend_direction == "UP":
                print("\n  IF you trade: MOMENTUM strategy (trend-following)")
                print("  Direction: LONG (buy when trending up)")
                print("  • Use stops to limit downside")
                print("  • Minimize trading frequency (high costs)")
                print("  • Only trade strong uptrends")
            elif trend_direction == "DOWN":
                print("\n  IF you trade: SHORT momentum")
                print("  Direction: SHORT (sell when trending down)")
                print("  • Use stops above entry")
                print("  • Minimize trading frequency")
                print("  • Consider avoiding entirely (downtrends risky)")
        elif (H and H < 0.45) or (mean_rev_up and mean_rev_down and 
              mean_rev_up < -0.005 and mean_rev_down > 0.005):
            print("\n  IF you trade: MEAN REVERSION strategy (fade extremes)")
            print("  Direction: Trade AGAINST the extremes")
            print("  • Only trade on extreme moves (top/bottom 10%)")
            print("  • Use tight stops")
            print("  • Minimize trading frequency")
        
        print("\n  REQUIRED: Paper trade first, verify out-of-sample performance")
    
    elif predictability_score == 2:
        print("\n? WEAK SIGNAL - Not worth trading risk")
        print("  Buy-and-hold is likely better than active trading")
    
    else:
        print("\n✗ NO CLEAR PREDICTABILITY - Random walk likely")
        print("  DO NOT attempt to trade this")
        print("  Buy-and-hold is your best option")
    
    if sharpe and sharpe > 1.0:
        print(f"\n(Sharpe {sharpe:.2f}: Historically good long-term investment)")
        print(" But past performance ≠ future results")
    elif sharpe:
        print(f"\n(Sharpe {sharpe:.2f}: Poor historical returns)")
        print(" Unlikely to offer good risk-adjusted returns going forward")
        
        # Extra warning if stock is in downtrend
        if trend_direction == "DOWN":
            print("\n⚠⚠⚠ MAJOR WARNING ⚠⚠⚠")
            print(f"This stock has NEGATIVE returns ({ret:.1f}% annual)")
            print(f"And is in a DOWNTREND ({recent_1y*100:.2f}% over 1 year)")
            print("Consider avoiding entirely or only shorting bounces")
    
    print("\n" + "="*80)
    print("KEY CAVEATS")
    print("="*80)
    print("""
1. All statistics are HISTORICAL - not predictive of future performance
2. In-sample results are biased upward (overfitting)
3. If a pattern is obvious, sophisticated traders have already exploited it
4. Costs, slippage, and taxes often eliminate thin edges
5. Market regimes change - past relationships may break down
6. Survivorship bias inflates historical returns
7. TREND DIRECTION MATTERS - momentum doesn't mean "always buy"

RECOMMENDATION: Use this as ONE input among many. Combine with:
  • Fundamental analysis
  • Market regime assessment
  • Proper position sizing & risk management
  • Real out-of-sample testing before committing capital
  • Conservative position sizing (risk 2% per trade maximum)
  • Clear stop-loss levels
  • Avoid trading stocks in severe downtrends (bankruptcy risk)
""")


if __name__ == "__main__":
    from analysis import analyze_stock
    interpret(analyze_stock("UBI.PA", window_days=5))
