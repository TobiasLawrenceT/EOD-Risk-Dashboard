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