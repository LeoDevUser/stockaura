import yfinance as yf
import numpy as np
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller
import matplotlib.pyplot as plt
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

def analyze_stock(ticker, period="5y", window_days=5):
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
        'momentum_corr': None,
        'lb_pvalue': None,
        'adf_pvalue': None,
        'mean_rev_up': None,
        'mean_rev_down': None,
        'sharpe': None,
        'volatility': None,
        'Return': None,
        'predictability_score': 0,
        'zscore': None,
        'OHLC': OHLC.to_dict('records')
    }

    #z-score (Requires 20 days of non-flat price action)
    if len(df) >= 20:
        roll_m = df['Close'].rolling(window=20).mean()
        roll_s = df['Close'].rolling(window=20).std()
        curr_std = roll_s.iloc[-1]
        if curr_std > 0: # Avoid division by zero warning
            z = (df['Close'].iloc[-1] - roll_m.iloc[-1]) / curr_std
            res['zscore'] = float(z)

    #Risk & Performance Metrics and Sharpe index (Requires at least 2 data points)
    if len(returns) > 2:
        std_dev = returns.std()
        avg_ret = returns.mean()
        res['volatility'] = float(std_dev * np.sqrt(252) * 100)
        res['Return'] = float(avg_ret * 252 * 100)
        if std_dev > 0:
            res['sharpe'] = float(avg_ret / std_dev * np.sqrt(252))

    #Ljung-Box
    if len(returns) > 10:
        lb_test = acorr_ljungbox(returns, lags=[10], return_df=True)
        res['lb_pvalue'] = float(lb_test.iloc[0, 1])
        if res['lb_pvalue'] < 0.05: res['predictability_score'] += 1

    #ADF
    if len(df['Close'].dropna()) > 20:
        try:
            adf_result = adfuller(df['Close'].dropna())
            res['adf_pvalue'] = float(adf_result[1])
        except Exception: pass

    #hurst
    if len(returns_window) > 100:
        try:
            H, _, _, _ = hurst_exponent(returns_window)
            if not np.isnan(H):
                res['hurst'] = float(H)
                if H > 0.55 or H < 0.45: res['predictability_score'] += 1
        except Exception: pass

    #Momentum & Mean Reversion
    if len(returns_window) > (window_days + 5):
        m_corr = np.corrcoef(returns_window[:-1], returns_window[1:])[0, 1]
        if not np.isnan(m_corr):
            res['momentum_corr'] = float(m_corr)
            if abs(m_corr) > 0.2: res['predictability_score'] += 1

        #Mean Reversion Analysis
        q75, q25 = np.percentile(returns_window, 75), np.percentile(returns_window, 25)
        large_up = returns_window > q75
        large_down = returns_window < q25
        valid_idx = np.arange(len(returns_window) - window_days)
        next_ret = returns_window[valid_idx + window_days]

        up_moves = next_ret[large_up[valid_idx]]
        dn_moves = next_ret[large_down[valid_idx]]

        if len(up_moves) > 0: res['mean_rev_up'] = float(up_moves.mean())
        if len(dn_moves) > 0: res['mean_rev_down'] = float(dn_moves.mean())

        #Score Mean Reversion
        if res['mean_rev_up'] is not None and res['mean_rev_down'] is not None:
            if abs(res['mean_rev_up']) > 0.005 and abs(res['mean_rev_down']) > 0.005:
                res['predictability_score'] += 1

    return res
