import yfinance as yf
import numpy as np
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller
import pandas as pd

def hurst_exponent(series, lags_min=10, lags_max=500):
    lags = range(lags_min, lags_max)
    tau = []
    
    for lag in lags:
        n_chunks = len(series) // lag
        if n_chunks == 0:
            continue
        
        chunk_rs = []
        for i in range(n_chunks):
            chunk = series[i*lag:(i+1)*lag]
            chunk_mean = np.mean(chunk)
            Y = np.cumsum(chunk - chunk_mean)
            R = np.max(Y) - np.min(Y)
            S = np.std(chunk, ddof=1)
            
            if S != 0:
                rs = R / S
                chunk_rs.append(rs)
        
        if len(chunk_rs) > 0:
            tau.append(np.mean(chunk_rs))
    
    lags = np.array(lags[:len(tau)])
    tau = np.array(tau)
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    H = poly[0]
    
    return H, lags, tau, poly


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

def analyze_stock(ticker, period="5y", window_days=5, account_size=10000, risk_per_trade=0.02):
    try:
        df = yf.download([ticker], period=period, progress=False)
    except Exception:
        return {"error": "Connection error with data provider", "ticker": ticker}

    if df.empty:
        return {"error": "No data found, symbol may be delisted", "ticker": ticker}

    if len(df) < 5:
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
            "current_price": current,
            "min_account_needed": min_account_needed,
            "risk_per_trade": risk_per_trade
        }
    
    OHLC = df.reset_index()[['Date','Open', 'High', 'Close', 'Low']]
    OHLC['Date'] = pd.to_datetime(OHLC['Date']).dt.strftime('%Y-%m-%d')

    df['Return'] = df['Close'].pct_change()
    df['Return_Window'] = df['Close'].pct_change(window_days)

    returns = df['Return'].dropna().values
    returns_window = df['Return_Window'].dropna().values

    res = {
        'ticker': ticker,
        'window_days': window_days,
        'period': period,
        'hurst': None,
        'hurst_oos': None,
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
        # Position Sizing Fields
        'suggested_shares': None,
        'stop_loss_price': None,
        'position_risk_amount': None,
        'position_size_warning': None,
        'volatility_category': None,
        'golden_cross_short': None,
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
        'currency': currency,
        'OHLC': OHLC.to_dict('records'),
        'data_points': len(df),
        'transaction_cost': 0.001,  # 0.1% per trade
        'slippage': 0.0005,  # 0.05%
        'risk_per_trade': risk_per_trade,  # Store user's risk tolerance
    }

    # Split data: 70% train, 30% test for out-of-sample validation
    split_idx = int(len(df) * 0.7)
    df_train = df.iloc[:split_idx]
    df_test = df.iloc[split_idx:]
    
    returns_train = df_train['Return'].dropna().values
    returns_window_train = df_train['Return_Window'].dropna().values
    returns_window_test = df_test['Return_Window'].dropna().values

    # CALCULATE RECENT RETURNS (for determining trend direction)
    current_price = df['Close'].iloc[-1]
    
    # 1 year ago (252 trading days)
    if len(df) >= 252:
        price_1y_ago = df['Close'].iloc[-252]
        recent_return_1y = (current_price - price_1y_ago) / price_1y_ago
        res['recent_return_1y'] = float(recent_return_1y)
    
    # 6 months ago (126 trading days)
    if len(df) >= 126:
        price_6m_ago = df['Close'].iloc[-126]
        recent_return_6m = (current_price - price_6m_ago) / price_6m_ago
        res['recent_return_6m'] = float(recent_return_6m)
    
    # 3 months ago (63 trading days)
    if len(df) >= 63:
        price_3m_ago = df['Close'].iloc[-63]
        recent_return_3m = (current_price - price_3m_ago) / price_3m_ago
        res['recent_return_3m'] = float(recent_return_3m)
    
    # 1 month ago (21 trading days)
    if len(df) >= 21:
        price_1m_ago = df['Close'].iloc[-21]
        recent_return_1m = (current_price - price_1m_ago) / price_1m_ago
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
    if res['volatility'] is not None and current_price and current_price > 0:
        # Daily volatility = Annual / sqrt(252)
        daily_vol_pct = (res['volatility'] / 100) / np.sqrt(252)
        
        # Stop loss distance = current price * (2x daily volatility)
        stop_loss_dist = current_price * (daily_vol_pct * 2)
        
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
                position_value = whole_shares * current_price
                
                if position_value <= account_size:
                    # User can afford this position
                    res['suggested_shares'] = whole_shares
                    
                    # CRITICAL FIX: Store both long and short stop loss prices
                    # For LONGS: stop loss is BELOW current price (limit downside)
                    # For SHORTS: stop loss is ABOVE current price (limit upside)
                    res['stop_loss_price_long'] = float(current_price - stop_loss_dist)
                    res['stop_loss_price_short'] = float(current_price + stop_loss_dist)
                    
                    # Default to long for now (will be updated after signal generation)
                    res['stop_loss_price'] = float(current_price - stop_loss_dist)
                    
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
                    affordable_shares = int(account_size / current_price)
                    
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
                            f"Cannot afford even 1 share (${current_price:,.2f}). "
                            f"Need minimum ${current_price * (1 + risk_per_trade):,.0f} account to trade this stock "
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

    # GOLDEN CROSS / DEATH CROSS
    if len(df) >= 50:
        sma_20 = df['Close'].rolling(window=20).mean().iloc[-1]
        sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ema_20 = df['Close'].ewm(span=20).mean().iloc[-1]
        
        if sma_20 is not None and sma_50 is not None:
            res['golden_cross_short'] = float(sma_20) < float(sma_50)

    # Ljung-Box Test
    if len(returns_train) > 10:
        lb_test = acorr_ljungbox(returns_train, lags=[10], return_df=True)
        res['lb_pvalue'] = float(lb_test.iloc[0, 1])
        if res['lb_pvalue'] < 0.05: 
            res['predictability_score'] += 1

    # ADF Test
    if len(df['Close'].dropna()) > 20:
        try:
            adf_result = adfuller(df['Close'].dropna())
            res['adf_pvalue'] = float(adf_result[1])
        except Exception: 
            pass

    # Hurst Exponent
    if len(returns_window_train) > 100:
        try:
            H, _, _, _ = hurst_exponent(returns_window_train)
            if not np.isnan(H):
                res['hurst'] = float(H)
                if H > 0.55 or H < 0.45: 
                    res['predictability_score'] += 1
        except Exception: 
            pass
    
    # Hurst out-of-sample
    if len(returns_window_test) > 100:
        try:
            H_oos, _, _, _ = hurst_exponent(returns_window_test)
            if not np.isnan(H_oos):
                res['hurst_oos'] = float(H_oos)
        except Exception: 
            pass

    # Momentum & Mean Reversion
    if len(returns_window_train) > (window_days + 5):
        m_corr = np.corrcoef(returns_window_train[:-1], returns_window_train[1:])[0, 1]
        if not np.isnan(m_corr):
            res['momentum_corr'] = float(m_corr)
            if abs(m_corr) > 0.2: 
                res['predictability_score'] += 1

        # Mean Reversion Analysis
        q75, q25 = np.percentile(returns_window_train, 75), np.percentile(returns_window_train, 25)
        large_up = returns_window_train > q75
        large_down = returns_window_train < q25
        valid_idx = np.arange(len(returns_window_train) - window_days)
        next_ret = returns_window_train[valid_idx + window_days]

        up_moves = next_ret[large_up[valid_idx]]
        dn_moves = next_ret[large_down[valid_idx]]

        if len(up_moves) > 0: 
            res['mean_rev_up'] = float(up_moves.mean())
        if len(dn_moves) > 0: 
            res['mean_rev_down'] = float(dn_moves.mean())

        # Score Mean Reversion
        if res['mean_rev_up'] is not None and res['mean_rev_down'] is not None:
            if abs(res['mean_rev_up']) > 0.005 and abs(res['mean_rev_down']) > 0.005:
                res['predictability_score'] += 1

    # OUT-OF-SAMPLE TESTING
    if len(returns_window_test) > (window_days + 5):
        m_corr_oos = np.corrcoef(returns_window_test[:-1], returns_window_test[1:])[0, 1]
        if not np.isnan(m_corr_oos):
            res['momentum_corr_oos'] = float(m_corr_oos)

        # Mean Reversion OOS
        q75_oos, q25_oos = np.percentile(returns_window_test, 75), np.percentile(returns_window_test, 25)
        large_up_oos = returns_window_test > q75_oos
        large_down_oos = returns_window_test < q25_oos
        valid_idx_oos = np.arange(len(returns_window_test) - window_days)
        next_ret_oos = returns_window_test[valid_idx_oos + window_days]

        up_moves_oos = next_ret_oos[large_up_oos[valid_idx_oos]]
        dn_moves_oos = next_ret_oos[large_down_oos[valid_idx_oos]]

        if len(up_moves_oos) > 0: 
            res['mean_rev_up_oos'] = float(up_moves_oos.mean())
        if len(dn_moves_oos) > 0: 
            res['mean_rev_down_oos'] = float(dn_moves_oos.mean())

    # REGIME STABILITY CHECK
    if res.get('momentum_corr') is not None and res.get('momentum_corr_oos') is not None:
        corr_in = abs(res['momentum_corr'])
        corr_oos = abs(res['momentum_corr_oos'])
        if corr_in > 0.01:
            stability = corr_oos / corr_in
            res['regime_stability'] = float(min(stability, 1.0))
        else:
            res['regime_stability'] = float(corr_oos)

    # LIQUIDITY ANALYSIS
    # Calculate 30-day average volume
    avg_vol_30 = df['Volume'].tail(30).mean()
    res['avg_daily_volume'] = float(avg_vol_30)
    
    # Amihud Illiquidity Ratio
    amihud = calculate_amihud_illiquidity(df)
    res['amihud_illiquidity'] = amihud
    
    # Position size as % of daily volume
    # IMPORTANT: Use the CALCULATED shares (before affordability check) for liquidity analysis
    # We want to know if the INTENDED position would be too large, not just the affordable one
    if res.get('calculated_shares') and avg_vol_30 > 0:
        position_size_vs_vol = res['calculated_shares'] / avg_vol_30
        res['position_size_vs_volume'] = float(position_size_vs_vol)
    elif res['suggested_shares'] and avg_vol_30 > 0:
        # Fallback: use suggested shares if we don't have calculated
        position_size_vs_vol = res['suggested_shares'] / avg_vol_30
        res['position_size_vs_volume'] = float(position_size_vs_vol)
    
    # Dynamic Slippage Estimate
    dynamic_slippage = calculate_dynamic_slippage(df)
    res['estimated_slippage_pct'] = dynamic_slippage * 100  # Convert to percentage
    
    # Total Friction (Slippage + Transaction Cost)
    # Transaction cost is a % per round trip (in + out = 2x cost)
    total_friction = (dynamic_slippage + res['transaction_cost']) * 2
    res['total_friction_pct'] = float(total_friction * 100)
    
    # Calculate Expected Edge (PRELIMINARY - will be zeroed if pattern fails)
    # Edge = Momentum correlation strength * Volatility (annual %)
    # This represents the expected win rate * average move per trade
    if res['momentum_corr'] is not None and res['volatility'] is not None:
        expected_edge = abs(res['momentum_corr']) * res['volatility']
        res['expected_edge_pct'] = float(expected_edge)
    
    # Is it liquid enough to trade? (PRELIMINARY - will be updated if pattern fails)
    # Rule: Position must be < 2% of daily volume AND edge > 3x friction
    # NOTE: This is about LIQUIDITY, not AFFORDABILITY
    # If user can't afford the position, that's separate (position_size_note handles it)
    if (res['position_size_vs_volume'] is not None and 
        res['expected_edge_pct'] is not None and
        res['total_friction_pct'] is not None):
        
        # Check if position is too large for the market
        position_too_large = res['position_size_vs_volume'] >= 0.02  # 2% threshold
        edge_too_small = res['expected_edge_pct'] <= (res['total_friction_pct'] * 3)
        
        if position_too_large:
            # Liquidity issue - position would move the market
            res['is_liquid_enough'] = False
            res['liquidity_failed'] = True  # Flag this as liquidity failure, not pattern failure
            
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
            # Edge too small - pattern might be weak but this is about costs
            res['is_liquid_enough'] = False
            res['liquidity_failed'] = False  # This is edge failure, not liquidity
        else:
            # All good
            res['is_liquid_enough'] = True
            res['liquidity_failed'] = False
    else:
        # If we don't have position sizing (unaffordable), don't fail liquidity check
        # The pattern might be good, just not executable with this account size
        res['is_liquid_enough'] = True  # Don't fail pattern validation due to small account
        res['liquidity_failed'] = False
    
    # Liquidity Quality Score
    res['liquidity_score'] = get_liquidity_score(amihud, res['position_size_vs_volume'])
    
    # Liquidity Warning (only for CRITICAL issues, not edge-vs-friction)
    if res['liquidity_score'] == 'LOW' or res['position_size_vs_volume'] and res['position_size_vs_volume'] > 0.02:
        res['liquidity_warning'] = get_liquidity_warning(
            res['liquidity_score'],
            res['position_size_vs_volume'] or 0,
            amihud
        )

    # GENERATE FINAL TRADING SIGNAL
    res['final_signal'] = generate_trading_signal(res)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CRITICAL FIX: Update stop loss based on final signal (LONG vs SHORT)
    # ═══════════════════════════════════════════════════════════════════════
    if res['final_signal'] and res.get('stop_loss_price_long') and res.get('stop_loss_price_short'):
        # Determine if signal is for SHORT positions
        short_signals = [
            'SHORT_DOWNTREND',
            'SHORT_BOUNCES_ONLY',
            'SHORT_MOMENTUM'
        ]
        
        if res['final_signal'] in short_signals:
            # SHORT position: stop loss is ABOVE entry (limit upside risk)
            res['stop_loss_price'] = res['stop_loss_price_short']
        else:
            # LONG position: stop loss is BELOW entry (limit downside risk)
            res['stop_loss_price'] = res['stop_loss_price_long']
    
    # ═══════════════════════════════════════════════════════════════════════
    # CRITICAL FIX: Zero out edge if pattern failed statistical validation
    # BUT NOT if liquidity failed (position too large) - that's a different issue
    # ═══════════════════════════════════════════════════════════════════════
    if res['final_signal'] in ['DO_NOT_TRADE', 'NO_CLEAR_SIGNAL'] and not res.get('liquidity_failed', False):
        # Pattern is unreliable - no exploitable edge exists
        res['expected_edge_pct'] = 0.0
        
        # Build detailed failure explanation
        validation_failures = []
        
        if res.get('predictability_score', 0) < 3:
            validation_failures.append(f"Predictability score {res['predictability_score']}/4 (need ≥3)")
        
        if res.get('regime_stability') is not None and res.get('regime_stability') < 0.7:
            validation_failures.append(f"Regime stability {res['regime_stability']*100:.0f}% (need ≥70%)")
        
        if res.get('lb_pvalue') is not None and res.get('lb_pvalue') >= 0.05:
            validation_failures.append(f"No autocorrelation (Ljung-Box p={res['lb_pvalue']:.3f})")
        
        if res.get('adf_pvalue') is not None and res.get('adf_pvalue') >= 0.05:
            validation_failures.append(f"Non-stationary (ADF p={res['adf_pvalue']:.3f})")
        
        if res.get('momentum_corr') is not None and abs(res['momentum_corr']) <= 0.1:
            validation_failures.append(f"Weak momentum (|r|={abs(res['momentum_corr']):.3f})")
        
        # Set comprehensive warning (only if NOT liquidity failure)
        if validation_failures:
            failure_msg = "; ".join(validation_failures)
            res['liquidity_warning'] = f"Pattern failed statistical validation: {failure_msg}. No exploitable edge exists."
        else:
            res['liquidity_warning'] = "Pattern failed statistical validation - no exploitable edge exists"
    
    return res


def generate_trading_signal(res):
    """
    Generate final trading signal based on all metrics.
    
    Core logic: 
    - Momentum determines if trends persist or reverse
    - Trend direction determines if we go LONG or SHORT
    - Hurst & Z-EMA refine entry/exit zones
    - Death cross is implicit in trend analysis (not a veto)
    
    CRITICAL CHECKS (in order):
    1. Predictability score must be >= 3 (high conviction, not participation trophy)
    2. Regime stability must be >= 0.7 (pattern must hold out-of-sample)
    3. Liquidity must be adequate (edge must cover friction costs)
    4. Momentum must be strong enough (> 0.1)
    5. Trend must be clear (UP or DOWN, not NEUTRAL)
    """
    
    # CHECK 1: Predictability Score - Requires HIGH conviction (3+ out of 4 tests)
    # Not a participation trophy! Needs strong evidence across multiple metrics
    if res.get('predictability_score', 0) < 3:
        return 'DO_NOT_TRADE'
    
    # CHECK 2: Regime Stability - Pattern must be robust out-of-sample
    # Stricter threshold (0.7 instead of 0.6): pattern must hold up in test period
    if res.get('regime_stability') is not None and res.get('regime_stability') < 0.7:
        return 'DO_NOT_TRADE'
    
    # CHECK 3: Liquidity & Edge Analysis - Friction costs must not eat profits
    # If edge doesn't cover friction, it's not tradeable no matter how good the pattern
    if not res.get('is_liquid_enough', False):
        return 'DO_NOT_TRADE'
    
    # CHECK 4: Momentum Detection - Must show persistence or reversal
    momentum = res.get('momentum_corr')
    if momentum is None or abs(momentum) <= 0.1:
        return 'NO_CLEAR_SIGNAL'
    
    # CHECK 5: Trend Direction - Must be clear (UP or DOWN)
    # NEUTRAL trends without strong momentum = skip
    trend = res.get('trend_direction')
    if trend not in ['UP', 'DOWN']:
        # NEUTRAL trend or no clear direction
        if abs(momentum) > 0.3:
            return 'WAIT_FOR_TREND'  # Strong momentum but unclear direction
        else:
            return 'DO_NOT_TRADE'  # Weak signal in ambiguous market
    
    # Now safe to reference other fields
    hurst = res.get('hurst')
    z_ema = res.get('z_ema')
    
    # UPTREND ANALYSIS (momentum > 0.1 = trends continue)
    if trend == 'UP':
        if momentum > 0.1:
            # Positive momentum in uptrend = FOLLOW THE UPTREND
            if hurst is not None and hurst > 0.55:
                # In trending regime - use Z-EMA to find good entries
                if z_ema is not None:
                    if z_ema > 1.0:
                        return 'WAIT_PULLBACK'      # Overbought, wait for pullback
                    elif z_ema > -0.5:
                        return 'BUY_UPTREND'        # In sweet spot, buy
                    else:
                        return 'BUY_PULLBACK'       # Dip in uptrend, good entry
                else:
                    return 'BUY_UPTREND'
            else:
                # Not in trending regime but momentum positive
                return 'BUY_MOMENTUM'
        else:
            # Negative momentum in uptrend = reversal signal
            return 'WAIT_OR_SHORT_BOUNCE'
    
    # DOWNTREND ANALYSIS (momentum > 0.1 = trends continue downward)
    elif trend == 'DOWN':
        if momentum > 0.1:
            # Positive momentum in downtrend = FOLLOW THE DOWNTREND
            # (Counter-intuitive but correct: momentum means trends persist)
            if hurst is not None and hurst > 0.55:
                # In trending regime - use Z-EMA to find good short entries
                if z_ema is not None:
                    if z_ema < -1.0:
                        return 'WAIT_SHORT_BOUNCE'      # Oversold, wait for bounce to short
                    elif z_ema < 0.5:
                        return 'SHORT_DOWNTREND'        # In sweet spot, short
                    else:
                        return 'SHORT_BOUNCES_ONLY'     # Bounce in downtrend, short the bounce
                else:
                    return 'SHORT_DOWNTREND'
            else:
                # Not in trending regime but momentum still positive (persistence)
                return 'SHORT_MOMENTUM'
        else:
            # Negative momentum in downtrend = reversal/bounce possible
            return 'WAIT_FOR_REVERSAL'
    
    # NEUTRAL TREND ANALYSIS (no clear direction)
    # This is the catch-all that was previously allowing ambiguous trades
    else:
        # Neutral trend = no clear signal for directional trading
        # Even if momentum is strong, we can't determine if it's up or down persistence
        if abs(momentum) > 0.3:
            # Strong momentum but no directional bias = wait for trend confirmation
            return 'WAIT_FOR_TREND'
        else:
            # Weak momentum + neutral trend = not tradeable
            return 'DO_NOT_TRADE'


if __name__ == "__main__":
    from info import interpret
    interpret(analyze_stock("PLTR", window_days=5))
