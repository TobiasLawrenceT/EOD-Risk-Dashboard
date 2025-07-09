HKD_USD = 0.1278
JPY_USD = 0.0066
portofolio = {
    "0700.HK": 100,     # Tencent shares
    "0005.HK": 80,      # HSBC
    "0388.HK": 50,      # HKEX
    "AAPL":    20,      # Apple
    "MSFT":    15,      # Microsoft
    "TLT":     30,      # 20-yr US Treasury ETF
    "USDJPY=X":10000,   # USD notional vs JPY
    "GC=F":    5        # Gold futures contracts
}

ticker_currency = {
    "0700.HK": "HKD",
    "0005.HK": "HKD",
    "0388.HK": "HKD",
    "AAPL":    "USD",
    "MSFT":    "USD",
    "TLT":     "USD",
    "USDJPY=X": "JPY",     # you're holding 10,000 USD *against* JPY
    "GC=F":    "USD"
}

benchmarks = {
    "HK":  "^HSI",      # Hang Seng Index
    "US":  "^GSPC"      # S&P-500
}

beta_map = {
    "0700.HK": "^HSI",
    "0005.HK": "^HSI",
    "0388.HK": "^HSI",
    "AAPL":    "^GSPC",
    "MSFT":    "^GSPC"
}

data_path = "data"