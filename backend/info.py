def interpret(results):
    """interpret statistical results"""
    
    ticker = results['ticker']
    window_days = results['window_days']

    print("="*80)
    print(f"{ticker} - STATISTICAL ANALYSIS ({window_days}-Day Window)")
    print("="*80)
    
    # TEST 1: Autocorrelation
    lb_pvalue = results['lb_pvalue']
    print("\n1. AUTOCORRELATION TEST (Ljung-Box)")
    print("-" * 80)
    print(f"\nResult: p-value = {lb_pvalue:.4f}")
    if lb_pvalue < 0.05:
        print("✓ Returns ARE autocorrelated (predictable)")
    else:
        print("✗ Returns are independent (random walk)")
    
    # TEST 2: ADF
    print("\n2. AUGMENTED DICKEY-FULLER TEST (Stationarity)")
    print("-" * 80)
    print(f"ADF p-value: {results['adf_pvalue']:.4f}")
    if results['adf_pvalue'] < 0.05:
        print("✓ Price is stationary (mean-reverting)")
    else:
        print("✗ Price has unit root (random walk)")
    
    # TEST 3: Mean Reversion
    print("\n3. MEAN REVERSION ANALYSIS")
    print("-" * 80)
    
    mean_rev_up = results['mean_rev_up']
    mean_rev_down = results['mean_rev_down']
    print(f"After large UP move (+top 25%): Next {window_days}-day return = {mean_rev_up:.4f} ({mean_rev_up*100:.2f}%)")
    print(f"After large DOWN move (-bottom 25%): Next {window_days}-day return = {mean_rev_down:.4f} ({mean_rev_down*100:.2f}%)")
    
    if mean_rev_up < -0.005 and mean_rev_down > 0.005:
        print("✓ STRONG mean reversion (extremes reverse)")
    elif mean_rev_up > 0.005 and mean_rev_down < -0.005:
        print("✓ STRONG momentum (extremes continue)")
    else:
        print("? Weak pattern (unclear)")
    
    # TEST 4: Momentum Correlation
    momentum_corr = results['momentum_corr']
    print("\n4. MOMENTUM ANALYSIS")
    print("-" * 80)
    print(f"Correlation between consecutive {window_days}-day returns: {momentum_corr:.4f}")
    
    if momentum_corr > 0.1:
        print("✓ MOMENTUM detected! Up moves tend to continue up.")
    elif momentum_corr < -0.1:
        print("✓ MEAN REVERSION detected! Up moves tend to reverse down.")
    else:
        print("✗ NO clear pattern. Essentially random.")
    
    # TEST 5: Hurst
    H = results['hurst']
    print("\n5. HURST EXPONENT (Trending vs Mean-Reverting)")
    print("-" * 80)
    print(f"Hurst Exponent: {H:.4f}")
    
    if H > 0.55:
        print(f"→ TRENDING (H = {H:.2f} > 0.55)")
    elif H < 0.45:
        print(f"→ MEAN-REVERTING (H = {H:.2f} < 0.45)")
    else:
        print(f"→ RANDOM WALK (H = {H:.2f} ≈ 0.5)")
    
    # TEST 6: Sharpe Ratio
    sharpe = results['sharpe']
    volatility = results['volatility']
    Return = results['Return']
    print("\n6. SHARPE RATIO (Investment Quality)")
    print("-" * 80)
    print(f"Sharpe Ratio: {sharpe:.3f}")
    print(f"Volatility (annualized): {volatility:.1f}%")
    print(f"Return (annualized): {Return:.1f}%")
    
    # CONCLUSION
    print("\n" + "="*80)
    print("CONCLUSION: IS THIS TRADEABLE?")
    print("="*80)
    
    predictability_score = results['predictability_score']
    
    print(f"\nPredictability Score: {predictability_score}/4")
    print(f"  H={H:.2f}, Corr={momentum_corr:.3f}, LB p={lb_pvalue:.4f}")
    
    if predictability_score >= 3:
        print("\n✓ HIGHLY PREDICTABLE - Use a trading strategy")
        if H > 0.55 and momentum_corr > 0.1:
            print("  → MOMENTUM strategy (follow trends, buy breakouts)")
        elif H < 0.45 or (mean_rev_up < -0.005 and mean_rev_down > 0.005):
            print("  → MEAN REVERSION strategy (fade extremes, sell highs/buy lows)")
    elif predictability_score == 2:
        print("\n? SOMEWHAT PREDICTABLE - Risky, use with caution")
    elif predictability_score == 1:
        print("\n✗ BARELY PREDICTABLE - Random walk likely")
        print("  Better to buy-and-hold than trade")
    else:
        print("\n✗✗ NOT PREDICTABLE - Pure random walk")
        print("  No strategy will work consistently")
    
    if sharpe > 1.0:
        print(f"\n(Sharpe {sharpe:.2f}: Good long-term investment regardless)")
    else:
        print(f"\n(Sharpe {sharpe:.2f}: Poor returns, skip this stock)")
    

if __name__ == "__main__":
    from analysis import analyze_stock
    interpret(analyze_stock("AA", window_days=5))
