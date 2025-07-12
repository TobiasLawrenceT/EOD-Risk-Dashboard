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
    "MSFT":    "^GSPC",
    "TLT":     "^GSPC"
}

data_path = "data"

scenarios = {

    # 1) Lehman week: Sep-08–2008 to Sep-12-2008  (approx. 5-day % moves)
    "Lehman_2008": {
        "0700.HK": -0.20,   # Tencent
        "0005.HK": -0.22,   # HSBC
        "0388.HK": -0.25,   # HKEX
        "AAPL":    -0.18,
        "MSFT":    -0.16,
        "TLT":      0.03,   # flight-to-quality
        "USDJPY=X": -0.04,  # JPY strengthens
        "GC=F":     0.10,   # gold rally
    },

    # 2) US–China tariff shock (Q2-2018 first salvo)
    "Tariff_2018": {
        "0700.HK": -0.12,
        "0005.HK": -0.10,
        "0388.HK": -0.11,
        "AAPL":    -0.05,
        "MSFT":    -0.04,
        "TLT":      0.02,
        "USDJPY=X":  0.03,  # risk-off JPY strengthens
        "GC=F":     0.04,
    },

    # 3) Oil-supply shock: Brent +15 %, equities sell off, gold up
    "OilSupplyDown": {
        "0700.HK": -0.06,
        "0005.HK": -0.05,
        "0388.HK": -0.06,
        "AAPL":    -0.07,
        "MSFT":    -0.07,
        "TLT":    -0.02,    # rates up on inflation fear
        "USDJPY=X":  0.02,
        "GC=F":     0.06,
    },
}
