#!/usr/bin/env python3
"""
Analyze top 500 stocks by market cap for trading opportunities
Optimized for the most liquid, tradeable stocks
"""

import json
import sys
from typing import Dict, List
import time
from datetime import datetime
import random

# Add backend to path
sys.path.insert(0, './backend')
from analysis import analyze_stock as run_analysis

# Configuration
TICKERS_FILE = "tickers.json"
TOP_N_STOCKS = 500  # Analyze top 500 by market cap
REQUEST_DELAY = 1.0  # 1 second between requests
MAX_RETRIES = 3
RETRY_DELAY = 5
DEFAULT_ACCOUNT_SIZE = 10000
DEFAULT_RISK_PER_TRADE = 0.02

last_request_time = 0


def load_tickers(filepath: str, limit: int = None) -> List[Dict[str, str]]:
    """Load tickers from JSON file (assumes sorted by market cap)"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    tickers = []
    for key, value in data.items():
        tickers.append({
            'ticker': value['ticker'],
            'title': value['title']
        })
        if limit and len(tickers) >= limit:
            break
    
    return tickers


def rate_limited_sleep():
    """Enforce rate limiting"""
    global last_request_time
    
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < REQUEST_DELAY:
        sleep_time = REQUEST_DELAY - time_since_last + random.uniform(0, 0.2)
        time.sleep(sleep_time)
    
    last_request_time = time.time()


def analyze_stock_with_retry(ticker: str, title: str, retry_count: int = 0) -> Dict:
    """Analyze with retry logic"""
    try:
        rate_limited_sleep()
        
        data = run_analysis(
            ticker=ticker,
            period='5y',
            window_days=5,
            account_size=DEFAULT_ACCOUNT_SIZE,
            risk_per_trade=DEFAULT_RISK_PER_TRADE
        )
        
        if data.get('error'):
            error_msg = str(data.get('error', '')).lower()
            if ('unauthorized' in error_msg or '401' in error_msg or 'crumb' in error_msg) and retry_count < MAX_RETRIES:
                print(f"   ⏳ Rate limited on {ticker}, waiting {RETRY_DELAY}s... (retry {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
                return analyze_stock_with_retry(ticker, title, retry_count + 1)
            return None
        
        score = calculate_score(data)
        
        return {
            'ticker': ticker,
            'title': title,
            'score': score,
            'final_signal': data.get('final_signal'),
            'predictability_score': data.get('predictability_score', 0),
            'regime_stability': data.get('regime_stability'),
            'momentum_corr': data.get('momentum_corr'),
            'expected_edge_pct': data.get('expected_edge_pct'),
            'current': data.get('current'),
            'currency': data.get('currency'),
            'trend_direction': data.get('trend_direction'),
            'sharpe': data.get('sharpe'),
            'volatility': data.get('volatility'),
            'liquidity_failed': data.get('liquidity_failed', False),
            'suggested_shares': data.get('suggested_shares'),
            'z_ema': data.get('z_ema'),
            'hurst': data.get('hurst'),
            'stop_loss_price': data.get('stop_loss_price')
        }
        
    except Exception as e:
        error_msg = str(e).lower()
        if ('unauthorized' in error_msg or '401' in error_msg or 'crumb' in error_msg) and retry_count < MAX_RETRIES:
            print(f"   ⏳ Rate limited on {ticker}, waiting {RETRY_DELAY}s... (retry {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return analyze_stock_with_retry(ticker, title, retry_count + 1)
        return None


def calculate_score(data: Dict) -> float:
    """Calculate composite score"""
    score = 0.0
    
    # Predictability (0-40)
    score += data.get('predictability_score', 0) * 10
    
    # Regime stability (0-20)
    if data.get('regime_stability') is not None:
        score += data.get('regime_stability') * 20
    
    # Edge vs friction (0-20)
    edge = data.get('expected_edge_pct', 0)
    friction = data.get('total_friction_pct', 0)
    if friction > 0:
        ratio = edge / friction
        if ratio > 3:
            score += min(20, (ratio - 3) * 4)
    
    # Signal quality (0-20)
    signal_scores = {
        'BUY_UPTREND': 20, 'BUY_PULLBACK': 20,
        'SHORT_DOWNTREND': 18, 'BUY_MOMENTUM': 15, 'SHORT_MOMENTUM': 15,
        'SHORT_BOUNCES_ONLY': 12, 'WAIT_PULLBACK': 8, 'WAIT_SHORT_BOUNCE': 8,
        'WAIT_OR_SHORT_BOUNCE': 5, 'WAIT_FOR_REVERSAL': 5, 'WAIT_FOR_TREND': 3,
        'NO_CLEAR_SIGNAL': 0, 'DO_NOT_TRADE': -50
    }
    score += signal_scores.get(data.get('final_signal', ''), 0)
    
    # Liquidity bonus
    if not data.get('liquidity_failed', False):
        score += 10
    
    # Volatility penalty
    if data.get('volatility') and data.get('volatility') > 50:
        score -= 5
    
    return score


def analyze_batch(tickers: List[Dict]) -> List[Dict]:
    """Analyze stocks sequentially with rate limiting"""
    results = []
    
    print(f"\n{'='*80}")
    print(f"Analyzing TOP {len(tickers)} stocks by market cap")
    print(f"Rate limit: {REQUEST_DELAY}s per request")
    print(f"Estimated time: ~{(len(tickers) * REQUEST_DELAY / 60):.0f} minutes")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    buy_count = short_count = wait_count = 0
    
    for i, ticker_info in enumerate(tickers, 1):
        result = analyze_stock_with_retry(ticker_info['ticker'], ticker_info['title'])
        
        if result:
            results.append(result)
            
            # Count signals
            signal = result.get('final_signal', '')
            if 'BUY' in signal:
                buy_count += 1
                icon = '🟢'
            elif 'SHORT' in signal:
                short_count += 1
                icon = '🔴'
            elif 'WAIT' in signal:
                wait_count += 1
                icon = '🟡'
            else:
                icon = '⚪'
            
            # Calculate ETA
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = len(tickers) - i
            eta_minutes = (remaining / rate / 60) if rate > 0 else 0
            
            print(f"[{i:3d}/{len(tickers)}] {icon} {ticker_info['ticker']:6s} "
                  f"Score: {result['score']:6.1f} | {signal:22s} "
                  f"| ETA: {eta_minutes:4.1f}m")
        else:
            print(f"[{i:3d}/{len(tickers)}] ✗ {ticker_info['ticker']:6s} FAILED")
        
        # Progress update every 50 stocks
        if i % 50 == 0:
            elapsed_mins = (time.time() - start_time) / 60
            print(f"\n📊 Progress: {i}/{len(tickers)} | "
                  f"Tradeable: {len(results)} | "
                  f"🟢 {buy_count} | 🔴 {short_count} | 🟡 {wait_count} | "
                  f"Time: {elapsed_mins:.1f}m\n")
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def save_results(results: List[Dict], filename: str = "top_stocks.json"):
    """Save to JSON"""
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_analyzed': len(results),
        'stocks': results[:50]  # Top 50 only
    }
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Saved top 50 to {filename}")
    return filename


def print_summary(results: List[Dict]):
    """Print top 50"""
    print(f"\n{'='*100}")
    print("🏆 TOP 50 TRADING OPPORTUNITIES")
    print(f"{'='*100}")
    print(f"{'#':<4} {'Ticker':<8} {'Score':<7} {'Signal':<22} {'Edge%':<8} {'Pred':<5} {'Trend':<6}")
    print(f"{'-'*100}")
    
    for i, s in enumerate(results[:50], 1):
        signal = s['final_signal'][:20] if s['final_signal'] else 'N/A'
        edge = f"{s.get('expected_edge_pct', 0):.1f}%" if s.get('expected_edge_pct') else 'N/A'
        
        # Color
        if 'BUY' in signal:
            sig = f"\033[92m{signal:22s}\033[0m"
        elif 'SHORT' in signal:
            sig = f"\033[91m{signal:22s}\033[0m"
        elif 'WAIT' in signal:
            sig = f"\033[93m{signal:22s}\033[0m"
        else:
            sig = f"{signal:22s}"
        
        print(f"{i:<4} {s['ticker']:<8} {s['score']:<7.1f} {sig} {edge:<8} "
              f"{s['predictability_score']}/4   {s.get('trend_direction', 'N/A'):<6}")
    
    print(f"{'='*100}\n")
    
    # Stats
    buy = sum(1 for s in results if 'BUY' in s.get('final_signal', ''))
    short = sum(1 for s in results if 'SHORT' in s.get('final_signal', ''))
    wait = sum(1 for s in results if 'WAIT' in s.get('final_signal', ''))
    
    print(f"📈 Signal Distribution:")
    print(f"   🟢 BUY:   {buy:2d} stocks")
    print(f"   🔴 SHORT: {short:2d} stocks")
    print(f"   🟡 WAIT:  {wait:2d} stocks")


def main():
    print(f"\n{'='*100}")
    print("STOCKAURA - TOP 500 MARKET CAP ANALYZER")
    print(f"{'='*100}\n")
    
    print("📂 Loading tickers...")
    tickers = load_tickers(TICKERS_FILE, limit=TOP_N_STOCKS)
    print(f"✅ Loaded {len(tickers)} stocks (top {TOP_N_STOCKS} by market cap)")
    
    input("\n⏸  Press ENTER to start analysis (~8 minutes)...")
    
    start = time.time()
    results = analyze_batch(tickers)
    elapsed = (time.time() - start) / 60
    
    print(f"\n⏱  Total time: {elapsed:.1f} minutes")
    print(f"📊 Analyzed: {len(tickers)} stocks")
    print(f"✅ Tradeable: {len(results)} opportunities found")
    
    save_results(results)
    print_summary(results)
    
    print(f"\n{'='*100}")
    print("📁 NEXT STEPS:")
    print(f"{'='*100}")
    print("1. Copy the file:       cp top_stocks.json frontend/public/")
    print("2. Start your app:      cd frontend && npm run dev")
    print("3. Visit:               http://localhost:5173/top-stocks")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
