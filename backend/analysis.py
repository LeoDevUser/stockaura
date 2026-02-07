import yfinance as yf
import numpy as np
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller
import pandas as pd

def format_number(num):
    num = float(num)
    if abs(num) >= 1e12:
        return f'{num/1e12:.2f}T'
    elif abs(num) >= 1e9:
        return f'{num/1e9:.2f}B'
    elif abs(num) >= 1e6:
        return f'{num/1e6:.2f}M'
    elif abs(num) >= 1e3:
        return f'{num/1e3:.2f}K'
    else:
        return f'{num}'


def dfa_hurst(series, min_box=10, max_box=None, num_scales=20):
    """
    Detrended Fluctuation Analysis (DFA) to estimate Hurst exponent.
    
    More robust than R/S analysis:
    - Less sensitive to short-term correlations and trends
    - Better performance on finite-length series
    - More stable across different parameter choices
    
    Returns: H, scales, fluctuations, poly
    - H: Hurst exponent (slope of log-log plot)
    - scales: box sizes used
    - fluctuations: DFA fluctuation at each scale
    - poly: polynomial fit coefficients
    """
    N = len(series)
    if max_box is None:
        max_box = N // 4  # Use at most 1/4 of series length
    
    if max_box <= min_box or N < min_box * 4:
        return np.nan, None, None, None
    
    # Step 1: Integrate the mean-centered series (cumulative sum of deviations)
    y = np.cumsum(series - np.mean(series))
    
    # Step 2: Generate logarithmically spaced box sizes
    scales = np.unique(
        np.logspace(np.log10(min_box), np.log10(max_box), num=num_scales).astype(int)
    )
    # Filter out scales that are too large
    scales = scales[scales <= N // 2]
    
    if len(scales) < 4:
        return np.nan, None, None, None
    
    fluctuations = []
    
    for box_size in scales:
        # Number of non-overlapping boxes
        n_boxes = N // box_size
        if n_boxes < 2:
            continue
        
        rms_values = []
        
        # Forward pass
        for i in range(n_boxes):
            start = i * box_size
            end = start + box_size
            segment = y[start:end]
            
            # Fit linear trend to segment
            x = np.arange(box_size)
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            
            # Calculate RMS of detrended segment
            rms = np.sqrt(np.mean((segment - trend) ** 2))
            rms_values.append(rms)
        
        # Backward pass (use remaining data from the end)
        for i in range(n_boxes):
            start = N - (i + 1) * box_size
            end = start + box_size
            if start < 0:
                break
            segment = y[start:end]
            
            x = np.arange(box_size)
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            
            rms = np.sqrt(np.mean((segment - trend) ** 2))
            rms_values.append(rms)
        
        if len(rms_values) > 0:
            # Overall fluctuation for this scale
            F = np.sqrt(np.mean(np.array(rms_values) ** 2))
            if F > 0:
                fluctuations.append(F)
            else:
                fluctuations.append(np.nan)
        else:
            fluctuations.append(np.nan)
    
    # Trim scales to match valid fluctuations
    scales = scales[:len(fluctuations)]
    fluctuations = np.array(fluctuations)
    
    # Remove NaN entries
    valid = ~np.isnan(fluctuations) & (fluctuations > 0)
    scales = scales[valid]
    fluctuations = fluctuations[valid]
    
    if len(scales) < 4:
        return np.nan, None, None, None
    
    # Step 3: Log-log fit to get Hurst exponent
    log_scales = np.log(scales.astype(float))
    log_fluct = np.log(fluctuations)
    
    poly = np.polyfit(log_scales, log_fluct, 1)
    H = poly[0]
    
    return H, scales, fluctuations, poly


def hurst_with_baseline(series, n_shuffles=50, **kwargs):
    """
    Compute DFA Hurst exponent with shuffled baseline comparison.
    
    Shuffling destroys temporal structure while preserving distribution.
    If the real Hurst is not significantly different from shuffled Hurst,
    the detected regime (trending/mean-reverting) is likely noise.
    
    Returns: H, H_shuffled_mean, H_shuffled_std, is_significant, scales, fluctuations, poly
    - H: real Hurst exponent
    - H_shuffled_mean: mean Hurst from shuffled series (should be ~0.5)
    - H_shuffled_std: std of shuffled Hurst values
    - is_significant: True if |H - 0.5| is statistically distinguishable from random
    """
    # Real Hurst
    H, scales, fluctuations, poly = dfa_hurst(series, **kwargs)
    
    if np.isnan(H):
        return H, np.nan, np.nan, False, None, None, None
    
    # Shuffled baseline
    shuffled_hursts = []
    rng = np.random.default_rng(42)  # Reproducible
    
    for _ in range(n_shuffles):
        shuffled = rng.permutation(series)
        H_shuf, _, _, _ = dfa_hurst(shuffled, **kwargs)
        if not np.isnan(H_shuf):
            shuffled_hursts.append(H_shuf)
    
    if len(shuffled_hursts) < 10:
        # Not enough valid shuffles — can't assess significance
        return H, np.nan, np.nan, False, scales, fluctuations, poly
    
    H_shuf_mean = np.mean(shuffled_hursts)
    H_shuf_std = np.std(shuffled_hursts)
    
    # Significant if real H is >1.5 standard deviations from shuffled mean
    # 1.5σ (~13% single-test FPR) is appropriate here because:
    # - This is one of 4 gates, not a standalone decision (combined FPR is much lower)
    # - 50 shuffles gives ~10% uncertainty on σ itself, making 2σ overly strict
    # - Could alternatively use 100 shuffles + 2σ for tighter estimates
    if H_shuf_std > 0:
        z_score = abs(H - H_shuf_mean) / H_shuf_std
        is_significant = z_score > 1.5
    else:
        is_significant = False
    
    return H, H_shuf_mean, H_shuf_std, is_significant, scales, fluctuations, poly


def multi_day_momentum_corr(daily_returns, block_days=3):
    """
    Calculate momentum correlation using NON-OVERLAPPING multi-day blocks.
    
    Measures: "Does the direction of this 3-day period predict the next 3-day period?"
    This is a medium-term signal (days-to-weeks timeframe).
    
    Why 3-day blocks (not 5-day):
    - 5-day blocks from 5Y training data → ~250 blocks → ~125 pairs → too noisy
    - 3-day blocks from 5Y training data → ~416 blocks → ~208 pairs → solid sample
    - 3 days still captures multi-day momentum, not just daily noise
    - No overlap = no bias, no corrections needed
    
    Returns: (correlation, n_pairs) or (None, 0)
    """
    n = len(daily_returns)
    n_blocks = n // block_days
    
    if n_blocks < 20:  # Need at least 10 pairs
        return None, 0
    
    # Build non-overlapping block returns
    blocks = []
    for i in range(n_blocks):
        start = i * block_days
        end = start + block_days
        block_return = np.prod(1 + daily_returns[start:end]) - 1
        blocks.append(block_return)
    
    blocks = np.array(blocks)
    
    # Consecutive block pairs: does block[i] predict block[i+1]?
    x = blocks[:-1]
    y = blocks[1:]
    
    if np.std(x) == 0 or np.std(y) == 0:
        return None, 0
    
    corr = np.corrcoef(x, y)[0, 1]
    
    if np.isnan(corr):
        return None, 0
    
    return float(corr), len(x)


def non_overlapping_mean_reversion(returns, window_days):
    """
    Mean reversion analysis using non-overlapping windows.
    
    After a large up/down block, what happens in the NEXT block?
    
    Returns: (mean_rev_up, mean_rev_down) or (None, None)
    """
    n = len(returns)
    n_blocks = n // window_days
    
    if n_blocks < 6:
        return None, None
    
    block_returns = []
    for i in range(n_blocks):
        start = i * window_days
        end = start + window_days
        block = returns[start:end]
        block_ret = np.prod(1 + block) - 1
        block_returns.append(block_ret)
    
    block_returns = np.array(block_returns)
    
    if len(block_returns) < 6:
        return None, None
    
    q75 = np.percentile(block_returns, 75)
    q25 = np.percentile(block_returns, 25)
    
    mean_rev_up = None
    mean_rev_down = None
    
    # After large up blocks
    up_next = []
    for i in range(len(block_returns) - 1):
        if block_returns[i] > q75:
            up_next.append(block_returns[i + 1])
    
    if len(up_next) > 0:
        mean_rev_up = float(np.mean(up_next))
    
    # After large down blocks
    down_next = []
    for i in range(len(block_returns) - 1):
        if block_returns[i] < q25:
            down_next.append(block_returns[i + 1])
    
    if len(down_next) > 0:
        mean_rev_down = float(np.mean(down_next))
    
    return mean_rev_up, mean_rev_down


def volume_price_confirmation(df, lookback=60):
    """
    Volume-Price Confirmation Test (5th predictability test)
    
    Measures: Does volume increase on moves in the trend direction?
    
    Method:
    - Split last `lookback` days into up-days and down-days
    - Compare average volume on up-days vs down-days
    - For uptrends: up-day volume should be higher (buyers are aggressive)
    - For downtrends: down-day volume should be higher (sellers are aggressive)
    
    Returns: {
        'vp_ratio': float,       # up_vol / down_vol (>1 = bullish confirmation)
        'vp_confirming': bool,   # Does volume confirm trend direction?
        'avg_vol_up': float,     # Average volume on up days
        'avg_vol_down': float,   # Average volume on down days
        'trend_for_vp': str      # Which trend was tested
    }
    """
    try:
        recent = df.tail(lookback).copy()
        
        if len(recent) < 20:
            return None
        
        recent['daily_return'] = recent['Close'].pct_change()
        recent = recent.dropna(subset=['daily_return', 'Volume'])
        
        up_days = recent[recent['daily_return'] > 0]
        down_days = recent[recent['daily_return'] < 0]
        
        if len(up_days) < 5 or len(down_days) < 5:
            return None
        
        avg_vol_up = float(up_days['Volume'].mean())
        avg_vol_down = float(down_days['Volume'].mean())
        
        if avg_vol_down == 0:
            return None
        
        vp_ratio = avg_vol_up / avg_vol_down
        
        # Determine recent trend from last 63 trading days (3 months)
        if len(df) >= 63:
            price_now = float(df['Close'].iloc[-1])
            price_3m = float(df['Close'].iloc[-63])
            trend_3m = (price_now - price_3m) / price_3m
        else:
            trend_3m = 0
        
        if trend_3m > 0.03:
            trend_for_vp = 'UP'
            # Uptrend confirmed: up-day volume > down-day volume by at least 10%
            vp_confirming = vp_ratio > 1.10
        elif trend_3m < -0.03:
            trend_for_vp = 'DOWN'
            # Downtrend confirmed: down-day volume > up-day volume by at least 10%
            vp_confirming = vp_ratio < 0.90
        else:
            trend_for_vp = 'NEUTRAL'
            # No clear trend — volume confirmation is ambiguous
            vp_confirming = False
        
        return {
            'vp_ratio': round(vp_ratio, 3),
            'vp_confirming': vp_confirming,
            'avg_vol_up': avg_vol_up,
            'avg_vol_down': avg_vol_down,
            'trend_for_vp': trend_for_vp,
        }
    except Exception:
        return None


def calculate_trade_quality(res):
    """
    Trade Quality Score (0-10) — How good is the current setup?
    
    This is SEPARATE from predictability. Predictability asks "does this stock 
    have exploitable patterns?" Quality asks "given it does, is NOW a good time?"
    
    Components (each 0-2 points):
    1. Multi-timeframe trend alignment (1M, 3M, 6M, 1Y agree?)
    2. Entry timing via Z-EMA (sweet spot vs overbought/oversold?)
    3. Risk-adjusted returns (Sharpe quality)
    4. Volatility appropriateness (moderate = best for trading)
    5. Volume-price confirmation (volume supports the trend?)
    
    Returns: {
        'trade_quality': float (0-10),
        'quality_components': dict of component scores,
        'quality_label': str ('Excellent'/'Good'/'Fair'/'Poor')
    }
    """
    components = {}
    total = 0.0
    
    # ── 1. MULTI-TIMEFRAME ALIGNMENT (0-2) ──────────────────────────────
    # Do 1M, 3M, 6M, 1Y returns all point the same direction?
    returns = []
    for key in ['recent_return_1m', 'recent_return_3m', 'recent_return_6m', 'recent_return_1y']:
        val = res.get(key)
        if val is not None:
            returns.append(val)
    
    if len(returns) >= 3:
        positive = sum(1 for r in returns if r > 0.02)
        negative = sum(1 for r in returns if r < -0.02)
        total_periods = len(returns)
        
        alignment = max(positive, negative) / total_periods
        
        if alignment >= 1.0:
            components['trend_alignment'] = 2.0  # All agree
        elif alignment >= 0.75:
            components['trend_alignment'] = 1.5  # 3/4 agree
        elif alignment >= 0.5:
            components['trend_alignment'] = 0.8  # Mixed
        else:
            components['trend_alignment'] = 0.3  # Conflicting
    else:
        components['trend_alignment'] = 0.5  # Insufficient data
    
    total += components['trend_alignment']
    
    # ── 2. ENTRY TIMING VIA Z-EMA (0-2) ─────────────────────────────────
    # In an uptrend: Z-EMA between -0.5 and 0.5 is ideal
    # In a downtrend: Z-EMA between -0.5 and 0.5 is ideal for shorting
    # Extremes (>1.5 or <-1.5) = bad entry timing
    z_ema = res.get('z_ema')
    trend = res.get('trend_direction')
    
    if z_ema is not None:
        abs_z = abs(z_ema)
        
        if trend == 'UP':
            if z_ema < -0.5:
                components['entry_timing'] = 2.0   # Pullback in uptrend = great entry
            elif z_ema < 0.5:
                components['entry_timing'] = 1.5   # Normal zone
            elif z_ema < 1.0:
                components['entry_timing'] = 1.0   # Slightly extended
            elif z_ema < 1.5:
                components['entry_timing'] = 0.5   # Overbought
            else:
                components['entry_timing'] = 0.0   # Very overbought
        elif trend == 'DOWN':
            if z_ema > 0.5:
                components['entry_timing'] = 2.0   # Bounce in downtrend = great short entry
            elif z_ema > -0.5:
                components['entry_timing'] = 1.5   # Normal zone
            elif z_ema > -1.0:
                components['entry_timing'] = 1.0   # Slightly extended
            elif z_ema > -1.5:
                components['entry_timing'] = 0.5   # Oversold
            else:
                components['entry_timing'] = 0.0   # Very oversold
        else:
            # Neutral trend — middle Z-EMA is fine, extremes are risky
            if abs_z < 0.5:
                components['entry_timing'] = 1.5
            elif abs_z < 1.0:
                components['entry_timing'] = 1.0
            else:
                components['entry_timing'] = 0.3
    else:
        components['entry_timing'] = 0.5
    
    total += components['entry_timing']
    
    # ── 3. RISK-ADJUSTED RETURNS / SHARPE (0-2) ─────────────────────────
    sharpe = res.get('sharpe')
    
    if sharpe is not None:
        if sharpe > 1.5:
            components['sharpe_quality'] = 2.0
        elif sharpe > 1.0:
            components['sharpe_quality'] = 1.5
        elif sharpe > 0.5:
            components['sharpe_quality'] = 1.0
        elif sharpe > 0:
            components['sharpe_quality'] = 0.5
        elif sharpe > -0.5:
            components['sharpe_quality'] = 0.2
        else:
            components['sharpe_quality'] = 0.0
    else:
        components['sharpe_quality'] = 0.5
    
    total += components['sharpe_quality']
    
    # ── 4. VOLATILITY APPROPRIATENESS (0-2) ──────────────────────────────
    # Moderate volatility (20-40%) is ideal: enough movement to profit,
    # not so much that stops get blown out
    vol = res.get('volatility')
    
    if vol is not None:
        if 20 <= vol <= 35:
            components['volatility_fit'] = 2.0    # Sweet spot
        elif 15 <= vol <= 45:
            components['volatility_fit'] = 1.5    # Acceptable
        elif 10 <= vol <= 55:
            components['volatility_fit'] = 0.8    # Marginal
        else:
            components['volatility_fit'] = 0.3    # Too calm or too wild
    else:
        components['volatility_fit'] = 0.5
    
    total += components['volatility_fit']
    
    # ── 5. VOLUME-PRICE CONFIRMATION (0-2) ───────────────────────────────
    vp = res.get('volume_price_data')
    
    if vp is not None and vp.get('vp_confirming') is not None:
        if vp['vp_confirming']:
            # Volume confirms trend
            ratio = vp['vp_ratio']
            if vp['trend_for_vp'] == 'UP':
                # How strongly does volume confirm uptrend?
                if ratio > 1.3:
                    components['volume_confirmation'] = 2.0
                elif ratio > 1.15:
                    components['volume_confirmation'] = 1.5
                else:
                    components['volume_confirmation'] = 1.0
            elif vp['trend_for_vp'] == 'DOWN':
                # How strongly does volume confirm downtrend?
                if ratio < 0.7:
                    components['volume_confirmation'] = 2.0
                elif ratio < 0.85:
                    components['volume_confirmation'] = 1.5
                else:
                    components['volume_confirmation'] = 1.0
            else:
                components['volume_confirmation'] = 0.5
        else:
            # Volume does NOT confirm trend — warning sign
            components['volume_confirmation'] = 0.2
    else:
        components['volume_confirmation'] = 0.5  # No data
    
    total += components['volume_confirmation']
    
    # ── FINAL SCORE ──────────────────────────────────────────────────────
    total = round(min(10.0, total), 1)
    
    if total >= 8.0:
        label = 'Excellent'
    elif total >= 6.0:
        label = 'Good'
    elif total >= 4.0:
        label = 'Fair'
    else:
        label = 'Poor'
    
    return {
        'trade_quality': total,
        'quality_components': components,
        'quality_label': label,
    }


def calculate_amihud_illiquidity(df):
    """
    Calculate Amihud Illiquidity ratio: |Return| / (Volume * Price)
    Higher value = more illiquid (price moves more per dollar of volume)
    
    Interpretation:
    - < 0.001: Highly liquid (large-cap stocks)
    - 0.001 - 0.01: Moderately liquid
    - > 0.01: Illiquid (hard to trade large positions)
    """
    try:
        df_temp = df.copy()
        df_temp['abs_return'] = np.abs(df_temp['Return'])
        df_temp['volume_times_price'] = df_temp['Volume'] * df_temp['Close']
        df_temp['illiquidity'] = df_temp['abs_return'] / (df_temp['volume_times_price'] + 1e-10)
        
        # Use last 30 days for recent liquidity assessment
        amihud = df_temp['illiquidity'].tail(30).mean()
        return float(amihud)
    except Exception:
        return None


def calculate_dynamic_slippage(df):
    """
    Estimate slippage based on volatility and daily price range.
    Higher volatility = wider spreads = more slippage
    
    Approach: Use 5% of average daily range as conservative estimate
    """
    try:
        df_temp = df.copy()
        # Daily range as % of close
        df_temp['daily_range_pct'] = (df_temp['High'] - df_temp['Low']) / df_temp['Close']
        avg_daily_range = df_temp['daily_range_pct'].tail(30).mean()
        
        # Assume you lose 5% of daily range to slippage (conservative)
        estimated_slippage = avg_daily_range * 0.05
        return float(estimated_slippage)
    except Exception:
        return 0.0005  # Fall back to default


def get_liquidity_score(amihud_illiquidity, position_size_vs_volume):
    """
    Determine liquidity quality based on Amihud ratio and position size
    
    Returns: 'HIGH', 'MEDIUM', 'LOW'
    """
    if amihud_illiquidity is None or position_size_vs_volume is None:
        return 'UNKNOWN'
    
    # HIGH liquidity: Amihud < 0.001 AND position < 0.5% of volume
    if amihud_illiquidity < 0.001 and position_size_vs_volume < 0.005:
        return 'HIGH'
    
    # MEDIUM liquidity: Amihud < 0.01 AND position < 2% of volume
    if amihud_illiquidity < 0.01 and position_size_vs_volume < 0.02:
        return 'MEDIUM'
    
    # LOW liquidity: Everything else
    return 'LOW'


def get_liquidity_warning(liquidity_score, position_size_vs_volume, amihud_illiquidity):
    """
    Generate warning message if liquidity is concerning
    Only warn for CRITICAL liquidity issues, not edge-vs-friction issues
    """
    warnings = []
    
    if position_size_vs_volume > 0.05:
        warnings.append("CRITICAL: Position exceeds 5% of daily volume - may not be executable")
    elif position_size_vs_volume > 0.02:
        warnings.append(f"Position is {position_size_vs_volume*100:.2f}% of daily volume - expect heavy slippage")
    
    if amihud_illiquidity and amihud_illiquidity > 0.01:
        warnings.append("Stock is illiquid - high price impact on large orders")
    
    return ' | '.join(warnings) if warnings else None


exchange_to_currency = {'T': 'JPY', 'NYB': '', 'CO': 'DKK', 'L': 'GBP or GBX', 'DE': 'EUR', 'PA': 'EUR', 'TO': 'CAD', 'V': 'CAD'}

def analyze_stock(ticker, period="5y", window_days=5, account_size=10000, risk_per_trade=0.02, n_shuffles=50):
    try:
        df = yf.download([ticker], period=period, progress=False)
    except Exception:
        return {"error": "Connection error with data provider", "ticker": ticker}

    if df.empty:
        return {"error": "No data found, symbol may be delisted", "ticker": ticker}

    if len(df) < 252:
        return {"error": "Insufficient historical data", "ticker": ticker}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    yfticker = yf.Ticker(ticker)
    tmp = ticker.split('.')
    currency = 'USD'
    if len(tmp) == 2:
        currency = exchange_to_currency[tmp[1]]
    title = yfticker.info.get('longName')
    current = yfticker.info.get('currentPrice')
    cap = format_number(yfticker.info.get('marketCap'))
    if current is None or current == 0:
        current = round(float(df['Close'].iloc[-1]),2)  # Use last closing price as fallback
    
    # CRITICAL VALIDATION: Account must be able to afford 1 share + risk buffer
    if current and account_size < current * (1 + risk_per_trade):
        min_account_needed = current * (1 + risk_per_trade)
        return {
            "error": (
                f"Account size (${account_size:,.2f}) is too small for this stock (${current:,.2f}/share). "
                f"Minimum needed: ${min_account_needed:,.2f} "
                f"(1 share + {risk_per_trade*100:.1f}% risk tolerance). "
                f"You need ${min_account_needed - account_size:,.2f} more."
            ),
            "ticker": ticker,
            "current": current,
            "cap": cap,
            "min_account_needed": min_account_needed,
            "risk_per_trade": risk_per_trade
        }
    
    OHLC = df.reset_index()[['Date','Open', 'High', 'Close', 'Low']]
    OHLC['Date'] = pd.to_datetime(OHLC['Date']).dt.strftime('%Y-%m-%d')

    df['Return'] = df['Close'].pct_change()

    returns = df['Return'].dropna().values

    res = {
        'ticker': ticker,
        'window_days': window_days,
        'period': period,
        'hurst': None,
        'hurst_oos': None,
        'hurst_significant': None,
        'hurst_shuffled_mean': None,
        'momentum_corr': None,
        'momentum_corr_oos': None,
        'lb_pvalue': None,
        'adf_pvalue': None,
        'mean_rev_up': None,
        'mean_rev_down': None,
        'mean_rev_up_oos': None,
        'mean_rev_down_oos': None,
        'sharpe': None,
        'volatility': None,
        'Return': None,
        'predictability_score': 0,
        'zscore': None,
        'z_ema': None,
        'regime_stability': None,
        'recent_return_1y': None,
        'recent_return_6m': None,
        'recent_return_3m': None,
        'recent_return_1m': None,
        'trend_direction': None,
        # Volume-Price Confirmation
        'volume_price_data': None,
        'vp_ratio': None,
        'vp_confirming': None,
        # Trade Quality Score
        'trade_quality': None,
        'quality_components': None,
        'quality_label': None,
        # Position Sizing Fields
        'suggested_shares': None,
        'stop_loss_price': None,
        'position_risk_amount': None,
        'position_size_warning': None,
        'volatility_category': None,
        'final_signal': None,
        # Liquidity & Friction Analysis
        'avg_daily_volume': None,
        'amihud_illiquidity': None,
        'liquidity_score': None,
        'position_size_vs_volume': None,
        'estimated_slippage_pct': None,
        'total_friction_pct': None,
        'expected_edge_pct': None,
        'is_liquid_enough': None,
        'liquidity_failed': False,  # True = position too large for market, False = pattern issue
        'calculated_shares': None,  # Shares before affordability check (for liquidity analysis)
        'liquidity_warning': None,
        'title': title,
        'current': current,
        'cap': cap,
        'currency': currency,
        'OHLC': OHLC.to_dict('records'),
        'data_points': len(df),
        'transaction_cost': 0.001,  # 0.1% per trade
        'slippage': 0.0005,  # 0.05%
        'risk_per_trade': risk_per_trade,  # Store user's risk tolerance
        'account_size_input': account_size,  # Store for speculative position halving
    }

    # Split data: 70% train, 30% test for out-of-sample validation
    split_idx = int(len(df) * 0.7)
    df_train = df.iloc[:split_idx]
    df_test = df.iloc[split_idx:]
    
    returns_train = df_train['Return'].dropna().values
    returns_test = df_test['Return'].dropna().values

    # CALCULATE RECENT RETURNS (for determining trend direction)
    current = df['Close'].iloc[-1]
    
    # 1 year ago (252 trading days)
    if len(df) >= 252:
        price_1y_ago = df['Close'].iloc[-252]
        recent_return_1y = (current - price_1y_ago) / price_1y_ago
        res['recent_return_1y'] = float(recent_return_1y)
    
    # 6 months ago (126 trading days)
    if len(df) >= 126:
        price_6m_ago = df['Close'].iloc[-126]
        recent_return_6m = (current - price_6m_ago) / price_6m_ago
        res['recent_return_6m'] = float(recent_return_6m)
    
    # 3 months ago (63 trading days)
    if len(df) >= 63:
        price_3m_ago = df['Close'].iloc[-63]
        recent_return_3m = (current - price_3m_ago) / price_3m_ago
        res['recent_return_3m'] = float(recent_return_3m)
    
    # 1 month ago (21 trading days)
    if len(df) >= 21:
        price_1m_ago = df['Close'].iloc[-21]
        recent_return_1m = (current - price_1m_ago) / price_1m_ago
        res['recent_return_1m'] = float(recent_return_1m)
    
    # Determine trend direction based on recent performance
    if res['recent_return_1y'] is not None:
        if res['recent_return_1y'] > 0.05:
            res['trend_direction'] = 'UP'
        elif res['recent_return_1y'] < -0.05:
            res['trend_direction'] = 'DOWN'
        else:
            res['trend_direction'] = 'NEUTRAL'

    # Z-SCORE (Simple 20-day MA)
    if len(df) >= 20:
        roll_m = df['Close'].rolling(window=20).mean()
        roll_s = df['Close'].rolling(window=20).std()
        curr_std = roll_s.iloc[-1]
        if curr_std > 0:
            z = (df['Close'].iloc[-1] - roll_m.iloc[-1]) / curr_std
            res['zscore'] = float(z)

    # Z-EMA (Exponential 20-day MA)
    if len(df) >= 20:
        ema_m = df['Close'].ewm(span=20).mean()
        ema_s = df['Close'].ewm(span=20).std()
        ema_std = ema_s.iloc[-1]
        if ema_std > 0:
            z_ema = (df['Close'].iloc[-1] - ema_m.iloc[-1]) / ema_std
            res['z_ema'] = float(z_ema)

    # Risk & Performance Metrics and Sharpe index
    if len(returns) > 2:
        std_dev = returns.std()
        avg_ret = returns.mean()
        res['volatility'] = float(std_dev * np.sqrt(252) * 100)
        res['Return'] = float(avg_ret * 252 * 100)
        if std_dev > 0:
            res['sharpe'] = float(avg_ret / std_dev * np.sqrt(252))

    # VOLATILITY CATEGORY
    if res['volatility'] is not None:
        vol = res['volatility']
        if vol < 15:
            res['volatility_category'] = 'VERY_LOW'
        elif vol < 25:
            res['volatility_category'] = 'LOW'
        elif vol < 35:
            res['volatility_category'] = 'MODERATE'
        elif vol < 50:
            res['volatility_category'] = 'HIGH'
        else:
            res['volatility_category'] = 'VERY_HIGH'

    # POSITION SIZING
    if res['volatility'] is not None and current and current > 0:
        # Daily volatility = Annual / sqrt(252)
        daily_vol_pct = (res['volatility'] / 100) / np.sqrt(252)
        
        # Stop loss distance = current price * (2x daily volatility)
        stop_loss_dist = current * (daily_vol_pct * 2)
        
        if stop_loss_dist > 0:
            # Position size = $ Risk / $ Distance
            risk_amount = account_size * risk_per_trade
            shares_to_buy = risk_amount / stop_loss_dist
            
            # Store calculated shares for liquidity analysis (before rounding/affordability)
            res['calculated_shares'] = shares_to_buy
            
            # Whole shares only (realistic trading)
            whole_shares = int(shares_to_buy)
            
            if whole_shares >= 1:
                # Check if user can actually afford this position
                position_value = whole_shares * current
                
                if position_value <= account_size:
                    # User can afford this position
                    res['suggested_shares'] = whole_shares
                    
                    # CRITICAL FIX: Store both long and short stop loss prices
                    res['stop_loss_price_long'] = float(current - stop_loss_dist)
                    res['stop_loss_price_short'] = float(current + stop_loss_dist)
                    
                    # Default to long for now (will be updated after signal generation)
                    res['stop_loss_price'] = float(current - stop_loss_dist)
                    
                    res['position_risk_amount'] = float(risk_amount)
                    
                    # Calculate position metrics
                    position_pct = (position_value / account_size) * 100
                    
                    # Add educational notes
                    if position_pct > 50:
                        res['position_size_note'] = (
                            f"Position is {position_pct:.1f}% of account. "
                            f"High concentration risk - consider diversification (most traders use 20-30% max per position)."
                        )
                    elif position_pct > 30:
                        res['position_size_note'] = (
                            f"Position is {position_pct:.1f}% of account. "
                            f"Moderate concentration - acceptable for high-conviction trades."
                        )
                    
                    # If fractional shares were rounded down significantly
                    if shares_to_buy >= 1.5 and whole_shares < shares_to_buy:
                        rounded_down = shares_to_buy - whole_shares
                        res['position_size_note'] = (
                            f"{res.get('position_size_note', '')} "
                            f"Note: Calculated {shares_to_buy:.2f} shares, rounded down to {whole_shares} (lost {rounded_down:.2f} shares)."
                        ).strip()
                else:
                    # Position value exceeds account - can't afford it
                    res['suggested_shares'] = None
                    res['stop_loss_price'] = None
                    res['stop_loss_price_long'] = None
                    res['stop_loss_price_short'] = None
                    res['position_risk_amount'] = None
                    
                    # Calculate how many shares they can actually afford
                    affordable_shares = int(account_size / current)
                    
                    # Calculate what account size they'd need for this risk level
                    min_account_for_risk = position_value
                    
                    if affordable_shares >= 1:
                        res['position_size_note'] = (
                            f"Position value (${position_value:,.0f}) exceeds account size (${account_size:,.0f}). "
                            f"With {risk_per_trade*100:.1f}% risk tolerance, you need ${shares_to_buy:.2f} shares "
                            f"but can only afford {affordable_shares} share{'s' if affordable_shares > 1 else ''}. "
                            f"Options: (1) Increase account to ${min_account_for_risk:,.0f}, "
                            f"(2) Reduce risk to {(affordable_shares * stop_loss_dist / account_size)*100:.1f}%, "
                            f"or (3) Trade a cheaper stock."
                        )
                    else:
                        res['position_size_note'] = (
                            f"Position value (${position_value:,.0f}) exceeds account size (${account_size:,.0f}). "
                            f"Cannot afford even 1 share (${current:,.2f}). "
                            f"Need minimum ${current * (1 + risk_per_trade):,.0f} account to trade this stock "
                            f"with {risk_per_trade*100:.1f}% risk."
                        )
            else:
                # Fractional shares - can't execute
                res['suggested_shares'] = None
                res['stop_loss_price'] = None
                res['stop_loss_price_long'] = None
                res['stop_loss_price_short'] = None
                res['position_risk_amount'] = None
                
                # Calculate minimum account needed for 1 share
                min_account_for_one_share = stop_loss_dist / risk_per_trade
                
                res['position_size_note'] = (
                    f"Calculated {shares_to_buy:.4f} shares (fractional). "
                    f"Need minimum 1 whole share to trade. "
                    f"Minimum account size: ${min_account_for_one_share:,.0f} "
                    f"(with {risk_per_trade*100:.1f}% risk tolerance)."
                )

    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTABILITY SCORE (5 tests, each worth 1 point)
    #
    # 1. Momentum correlation (3-day blocks, |r| > 0.08)
    # 2. Hurst/DFA (significant + regime detected)
    # 3. Mean reversion (conditional reversal after extremes)
    # 4. Regime stability OOS (pattern holds out-of-sample)
    # 5. Volume-price confirmation (volume supports trend direction)
    #
    # Ljung-Box: still computed (informational) but NOT scored
    #   — it's redundant with momentum correlation
    # ADF: still computed (informational) but NOT scored
    #   — most stocks are non-stationary, it rarely contributes
    # ═══════════════════════════════════════════════════════════════════════

    # Ljung-Box Test (informational only — NOT scored)
    if len(returns_train) > 10:
        lb_test = acorr_ljungbox(returns_train, lags=[10], return_df=True)
        res['lb_pvalue'] = float(lb_test.iloc[0, 1])

    # ADF Test (informational only — NOT scored)
    if len(df['Close'].dropna()) > 20:
        try:
            adf_result = adfuller(df['Close'].dropna())
            res['adf_pvalue'] = float(adf_result[1])
        except Exception: 
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # HURST EXPONENT (DFA with shuffled baseline)
    # Uses Detrended Fluctuation Analysis instead of R/S for stability.
    # Compares against shuffled baseline to verify significance.
    # ═══════════════════════════════════════════════════════════════════════
    if len(returns_train) > 100:
        try:
            H, H_shuf_mean, H_shuf_std, is_sig, _, _, _ = hurst_with_baseline(
                returns_train, n_shuffles=n_shuffles
            )
            if not np.isnan(H):
                res['hurst'] = float(H)
                res['hurst_significant'] = bool(is_sig)
                if not np.isnan(H_shuf_mean):
                    res['hurst_shuffled_mean'] = float(H_shuf_mean)
                
                # Only count toward predictability if significantly different from random
                if is_sig and (H > 0.55 or H < 0.45):
                    res['predictability_score'] += 1
        except Exception:
            pass
    
    # Hurst out-of-sample (use fewer shuffles — just need regime check, not full significance)
    oos_shuffles = max(10, n_shuffles // 3)
    if len(returns_test) > 100:
        try:
            H_oos, _, _, _, _, _, _ = hurst_with_baseline(returns_test, n_shuffles=oos_shuffles)
            if not np.isnan(H_oos):
                res['hurst_oos'] = float(H_oos)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # MOMENTUM CORRELATION (Non-overlapping 3-day blocks)
    # Measures: "Does the direction of this 3-day period predict the next?"
    # 3-day blocks give ~400+ pairs from 5Y training data — enough for reliable
    # correlation while capturing multi-day momentum (not just daily noise).
    # No overlap = no bias correction needed.
    #
    # Typical 3-day block correlations: 0.05–0.15 for trending stocks
    # Threshold: 0.08 (with ~400 pairs, t ≈ 0.08 * sqrt(400) ≈ 1.6)
    # ═══════════════════════════════════════════════════════════════════════
    if len(returns_train) > 30:
        m_corr, n_pairs = multi_day_momentum_corr(returns_train, block_days=3)
        if m_corr is not None:
            res['momentum_corr'] = float(m_corr)
            if abs(m_corr) > 0.08:
                res['predictability_score'] += 1

        # Mean Reversion Analysis (non-overlapping blocks — appropriate here
        # because we're asking "after a big 5-day move, what happens next?")
        mean_rev_up, mean_rev_down = non_overlapping_mean_reversion(returns_train, window_days)
        res['mean_rev_up'] = mean_rev_up
        res['mean_rev_down'] = mean_rev_down

        # Score Mean Reversion
        if res['mean_rev_up'] is not None and res['mean_rev_down'] is not None:
            if abs(res['mean_rev_up']) > 0.003 and abs(res['mean_rev_down']) > 0.003:
                res['predictability_score'] += 1

    # OUT-OF-SAMPLE TESTING
    if len(returns_test) > 30:
        m_corr_oos, _ = multi_day_momentum_corr(returns_test, block_days=3)
        if m_corr_oos is not None:
            res['momentum_corr_oos'] = float(m_corr_oos)

        # Mean Reversion OOS (non-overlapping blocks)
        mean_rev_up_oos, mean_rev_down_oos = non_overlapping_mean_reversion(returns_test, window_days)
        res['mean_rev_up_oos'] = mean_rev_up_oos
        res['mean_rev_down_oos'] = mean_rev_down_oos

    # REGIME STABILITY CHECK
    # Asks: "Does the momentum pattern exist in BOTH periods with the SAME direction?"
    # 
    # Existence-based (not ratio-based):
    # - Same sign AND OOS passes minimum threshold → STABLE (1.0)
    # - Same sign but OOS below threshold → WEAK (0.5) 
    # - Sign flip → UNSTABLE (0.0)
    #
    # With 3-day non-overlapping blocks, typical correlations are 0.05–0.15.
    # OOS threshold: 0.05 (meaningful multi-day momentum at 3-day scale)
    MOMENTUM_MIN_THRESHOLD = 0.05
    
    if res.get('momentum_corr') is not None and res.get('momentum_corr_oos') is not None:
        corr_in = res['momentum_corr']
        corr_oos = res['momentum_corr_oos']
        
        if abs(corr_in) > MOMENTUM_MIN_THRESHOLD:
            same_sign = (corr_in > 0 and corr_oos > 0) or (corr_in < 0 and corr_oos < 0)
            
            if same_sign and abs(corr_oos) >= MOMENTUM_MIN_THRESHOLD:
                # Pattern exists in both periods, same direction, both meaningful
                res['regime_stability'] = 1.0
            elif same_sign:
                # Same direction but OOS is weak — partial confidence
                res['regime_stability'] = 0.5
            else:
                # Sign flipped — pattern reversed out-of-sample
                res['regime_stability'] = 0.0
        else:
            # In-sample momentum too weak to assess stability
            res['regime_stability'] = 0.0
    
    # Also check Hurst stability if available
    # If Hurst is significant in-sample, does the regime hold OOS?
    if (res.get('hurst') is not None and res.get('hurst_oos') is not None 
        and res.get('hurst_significant')):
        hurst_in = res['hurst']
        hurst_oos = res['hurst_oos']
        
        # Check if both agree on regime type (both trending, both mean-reverting, etc.)
        in_trending = hurst_in > 0.55
        in_reverting = hurst_in < 0.45
        oos_trending = hurst_oos > 0.55
        oos_reverting = hurst_oos < 0.45
        
        hurst_agrees = (in_trending and oos_trending) or (in_reverting and oos_reverting)
        
        # If Hurst regime disagrees OOS, cap stability at 0.5
        if not hurst_agrees and res.get('regime_stability', 0) > 0.5:
            res['regime_stability'] = 0.5

    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTABILITY TEST 4: Regime Stability OOS
    # Does the momentum pattern hold out-of-sample?
    # ═══════════════════════════════════════════════════════════════════════
    if res.get('regime_stability') is not None and res['regime_stability'] >= 0.5:
        res['predictability_score'] += 1

    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTABILITY TEST 5: Volume-Price Confirmation
    # Does volume increase on moves in the trend direction?
    # ═══════════════════════════════════════════════════════════════════════
    vp_data = volume_price_confirmation(df, lookback=60)
    if vp_data is not None:
        res['volume_price_data'] = vp_data
        res['vp_ratio'] = vp_data['vp_ratio']
        res['vp_confirming'] = vp_data['vp_confirming']
        
        if vp_data['vp_confirming']:
            res['predictability_score'] += 1

    # LIQUIDITY ANALYSIS
    # Calculate 30-day average volume
    avg_vol_30 = df['Volume'].tail(30).mean()
    res['avg_daily_volume'] = float(avg_vol_30)
    
    # Amihud Illiquidity Ratio
    amihud = calculate_amihud_illiquidity(df)
    res['amihud_illiquidity'] = amihud
    
    # Position size as % of daily volume
    if res.get('calculated_shares') and avg_vol_30 > 0:
        position_size_vs_vol = res['calculated_shares'] / avg_vol_30
        res['position_size_vs_volume'] = float(position_size_vs_vol)
    elif res['suggested_shares'] and avg_vol_30 > 0:
        position_size_vs_vol = res['suggested_shares'] / avg_vol_30
        res['position_size_vs_volume'] = float(position_size_vs_vol)
    
    # Dynamic Slippage Estimate
    dynamic_slippage = calculate_dynamic_slippage(df)
    res['estimated_slippage_pct'] = dynamic_slippage * 100  # Convert to percentage
    
    # Total Friction (Slippage + Transaction Cost)
    total_friction = (dynamic_slippage + res['transaction_cost']) * 2
    res['total_friction_pct'] = float(total_friction * 100)
    
    # Calculate Expected Edge (PRELIMINARY - will be zeroed if pattern fails)
    if res['momentum_corr'] is not None and res['volatility'] is not None:
        expected_edge = abs(res['momentum_corr']) * res['volatility']
        res['expected_edge_pct'] = float(expected_edge)
    
    # Is it liquid enough to trade?
    if (res['position_size_vs_volume'] is not None and 
        res['expected_edge_pct'] is not None and
        res['total_friction_pct'] is not None):
        
        position_too_large = res['position_size_vs_volume'] >= 0.02
        edge_too_small = res['expected_edge_pct'] <= (res['total_friction_pct'] * 3)
        
        if position_too_large:
            res['is_liquid_enough'] = False
            res['liquidity_failed'] = True
            
            vol_pct = res['position_size_vs_volume'] * 100
            if vol_pct > 100:
                res['liquidity_warning'] = (
                    f"Position would be {vol_pct:.1f}% of daily volume - exceeds entire daily trading! "
                    f"This would cause massive slippage. This tool is designed for retail/small institutional traders. "
                    f"Large institutions need multi-day VWAP execution, dark pools, or reduce position size to <2% of daily volume."
                )
            elif vol_pct > 10:
                res['liquidity_warning'] = (
                    f"Position would be {vol_pct:.1f}% of daily volume (need <2%). "
                    f"This would significantly move the market and cause severe slippage (est. 10-30%). "
                    f"Options: (1) Reduce risk tolerance to get smaller position, (2) Split order over multiple days, "
                    f"or (3) Trade a more liquid stock."
                )
            else:
                res['liquidity_warning'] = (
                    f"Position would be {vol_pct:.1f}% of daily volume (need <2%). "
                    f"This would impact the market. Consider reducing position size or spreading execution over time."
                )
        elif edge_too_small:
            res['is_liquid_enough'] = False
            res['liquidity_failed'] = False
        else:
            res['is_liquid_enough'] = True
            res['liquidity_failed'] = False
    else:
        res['is_liquid_enough'] = True
        res['liquidity_failed'] = False
    
    # Liquidity Quality Score
    res['liquidity_score'] = get_liquidity_score(amihud, res['position_size_vs_volume'])
    
    # Liquidity Warning (only for CRITICAL issues)
    if res['liquidity_score'] == 'LOW' or res['position_size_vs_volume'] and res['position_size_vs_volume'] > 0.02:
        res['liquidity_warning'] = get_liquidity_warning(
            res['liquidity_score'],
            res['position_size_vs_volume'] or 0,
            amihud
        )

    # GENERATE FINAL TRADING SIGNAL
    res['final_signal'] = generate_trading_signal(res)
    
    # ═══════════════════════════════════════════════════════════════════════
    # Update stop loss based on final signal (LONG vs SHORT)
    # ═══════════════════════════════════════════════════════════════════════
    if res['final_signal'] and res.get('stop_loss_price_long') and res.get('stop_loss_price_short'):
        short_signals = [
            'SHORT_DOWNTREND', 'SHORT_BOUNCES_ONLY', 'SHORT_MOMENTUM',
            'SPEC_SHORT_DOWNTREND', 'SPEC_SHORT_BOUNCES_ONLY', 'SPEC_SHORT_MOMENTUM',
            'WAIT_OR_SHORT_BOUNCE', 'SPEC_WAIT_OR_SHORT_BOUNCE'
        ]
        
        if res['final_signal'] in short_signals:
            res['stop_loss_price'] = res['stop_loss_price_short']
        else:
            res['stop_loss_price'] = res['stop_loss_price_long']
    
    # ═══════════════════════════════════════════════════════════════════════
    # SPECULATIVE TIER: Halve position size for 2/4 predictability signals
    # ═══════════════════════════════════════════════════════════════════════
    if res['final_signal'] and res['final_signal'].startswith('SPEC_'):
        if res.get('suggested_shares') is not None and res['suggested_shares'] > 1:
            full_shares = res['suggested_shares']
            half_shares = max(1, full_shares // 2)
            res['suggested_shares'] = half_shares
            res['speculative_full_shares'] = full_shares  # Store original for display
            
            # Update position note
            position_value = half_shares * (res.get('current') or 0)
            account = res.get('account_size_input', 10000)
            position_pct = (position_value / account) * 100 if account > 0 else 0
            res['position_size_note'] = (
                f"⚠ SPECULATIVE: Position halved from {full_shares} to {half_shares} shares "
                f"({position_pct:.1f}% of account). Only {res.get('predictability_score', 0)}/5 statistical tests passed — "
                f"reduced position size limits downside from weaker conviction."
            )
    
    # ═══════════════════════════════════════════════════════════════════════
    # TRADE QUALITY SCORE (0-10)
    # Synthesizes descriptive stats into a single "how good is this setup?"
    # Only meaningful for tradeable signals — skip for DO_NOT_TRADE
    # ═══════════════════════════════════════════════════════════════════════
    if res['final_signal'] and res['final_signal'] not in ('DO_NOT_TRADE', 'NO_CLEAR_SIGNAL'):
        quality = calculate_trade_quality(res)
        res['trade_quality'] = quality['trade_quality']
        res['quality_components'] = quality['quality_components']
        res['quality_label'] = quality['quality_label']
    
    # ═══════════════════════════════════════════════════════════════════════
    # Zero out edge if pattern failed statistical validation
    # BUT NOT if liquidity failed (position too large) - that's a different issue
    # ═══════════════════════════════════════════════════════════════════════
    if res['final_signal'] in ['DO_NOT_TRADE', 'NO_CLEAR_SIGNAL'] and not res.get('liquidity_failed', False):
        res['expected_edge_pct'] = 0.0
        
        validation_failures = []
        
        if res.get('predictability_score', 0) < 2:
            validation_failures.append(f"Predictability score {res['predictability_score']}/5 (need ≥2)")
        
        if res.get('regime_stability') is not None and res.get('regime_stability') < 0.5:
            if res.get('regime_stability') == 0.0:
                validation_failures.append("Regime stability 0% — momentum direction REVERSED out-of-sample")
            else:
                validation_failures.append(f"Regime stability {res['regime_stability']*100:.0f}% (need ≥50%)")
        
        if res.get('momentum_corr') is not None and abs(res['momentum_corr']) <= 0.08:
            validation_failures.append(f"Weak momentum (|r|={abs(res['momentum_corr']):.3f}, need >0.08)")
        
        if res.get('hurst_significant') is False:
            validation_failures.append("Hurst exponent not distinguishable from random (failed baseline test)")
        
        if res.get('vp_confirming') is False or res.get('vp_confirming') is None:
            vp_ratio = res.get('vp_ratio')
            if vp_ratio is not None:
                validation_failures.append(f"Volume doesn't confirm trend (up/down vol ratio: {vp_ratio:.2f})")
            else:
                validation_failures.append("Volume-price confirmation unavailable")
        
        if validation_failures:
            failure_msg = "; ".join(validation_failures)
            pattern_warning = f"Pattern failed statistical validation: {failure_msg}. No exploitable edge exists."
        else:
            pattern_warning = "Pattern failed statistical validation - no exploitable edge exists"

         # Append to existing liquidity warning instead of overwriting
        existing_warning = res.get('liquidity_warning')
        if existing_warning:
            res['liquidity_warning'] = f"{existing_warning} | {pattern_warning}"
        else:
            res['liquidity_warning'] = pattern_warning
    
    return res


def generate_trading_signal(res):
    """
    Generate final trading signal based on all metrics.
    
    PREDICTABILITY SCORE: Now 0-5 (was 0-4):
      1. Momentum correlation  2. Hurst/DFA  3. Mean reversion
      4. Regime stability OOS  5. Volume-price confirmation
    
    TWO TIERS:
    - HIGH CONVICTION (predictability ≥3/5): Full position, standard signals
    - SPECULATIVE (predictability 2/5): Reduced position, extra warnings
      Still requires: stability ≥50%, edge > 3x friction, momentum > 0.08
    
    Hard rejections (any predictability):
    - Regime stability 0% (sign flip) → DO_NOT_TRADE
    - Not liquid enough → DO_NOT_TRADE
    - Predictability < 2 → DO_NOT_TRADE
    """
    
    # HARD GATE: Minimum predictability
    pred_score = res.get('predictability_score', 0)
    if pred_score < 2:
        return 'DO_NOT_TRADE'
    
    # HARD GATE: Regime Stability (no sign flips)
    if res.get('regime_stability') is not None and res.get('regime_stability') < 0.5:
        return 'DO_NOT_TRADE'
    
    # HARD GATE: Liquidity & Edge
    if not res.get('is_liquid_enough', False):
        return 'DO_NOT_TRADE'
    
    # Determine tier
    is_speculative = pred_score < 3  # 2/4 = speculative
    
    # Momentum check
    momentum = res.get('momentum_corr')
    if momentum is None or abs(momentum) <= 0.08:
        return 'NO_CLEAR_SIGNAL'
    
    # Trend direction
    trend = res.get('trend_direction')
    if trend not in ['UP', 'DOWN']:
        if abs(momentum) > 0.15:
            return 'WAIT_FOR_TREND'
        else:
            return 'DO_NOT_TRADE'
    
    # Reference fields for entry refinement
    hurst = res.get('hurst')
    z_ema = res.get('z_ema')
    hurst_significant = res.get('hurst_significant', False)
    
    # ─── GENERATE SIGNAL ────────────────────────────────────────────────
    signal = None
    
    if trend == 'UP':
        if momentum > 0.08:
            if hurst_significant and hurst is not None and hurst > 0.55:
                if z_ema is not None:
                    if z_ema > 1.0:
                        signal = 'WAIT_PULLBACK'
                    elif z_ema > -0.5:
                        signal = 'BUY_UPTREND'
                    else:
                        signal = 'BUY_PULLBACK'
                else:
                    signal = 'BUY_UPTREND'
            else:
                signal = 'BUY_MOMENTUM'
        else:
            signal = 'WAIT_OR_SHORT_BOUNCE'
    
    elif trend == 'DOWN':
        if momentum > 0.08:
            if hurst_significant and hurst is not None and hurst > 0.55:
                if z_ema is not None:
                    if z_ema < -1.0:
                        signal = 'WAIT_SHORT_BOUNCE'
                    elif z_ema < 0.5:
                        signal = 'SHORT_DOWNTREND'
                    else:
                        signal = 'SHORT_BOUNCES_ONLY'
                else:
                    signal = 'SHORT_DOWNTREND'
            else:
                signal = 'SHORT_MOMENTUM'
        else:
            signal = 'WAIT_FOR_REVERSAL'
    
    else:
        if abs(momentum) > 0.15:
            signal = 'WAIT_FOR_TREND'
        else:
            signal = 'DO_NOT_TRADE'
    
    # ─── APPLY SPECULATIVE PREFIX ───────────────────────────────────────
    # For 2/4 predictability: prefix actionable signals with SPEC_
    # WAIT/DO_NOT_TRADE signals don't need speculative prefix
    if is_speculative and signal is not None:
        actionable_signals = [
            'BUY_UPTREND', 'BUY_PULLBACK', 'BUY_MOMENTUM',
            'SHORT_DOWNTREND', 'SHORT_BOUNCES_ONLY', 'SHORT_MOMENTUM',
            'WAIT_OR_SHORT_BOUNCE', 'WAIT_FOR_REVERSAL'
        ]
        if signal in actionable_signals:
            signal = 'SPEC_' + signal
    
    return signal or 'DO_NOT_TRADE'
