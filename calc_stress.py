"""
stress_test.py  –  quick-and-clean historical / hypothetical scenario engine
-----------------------------------------------------------------------------

• Reads today's positions and latest close from prices.csv
• Re-values the frozen book under three predefined crisis scenarios
• Outputs absolute and % P/L to an Excel sheet "Stress"
"""

import numpy as np
import pandas as pd
from pathlib import Path
import datetime as dt
import yfinance as yf
import sys

# ---------------------------------------------------------------------
# 0.  Project paths + imports
# ---------------------------------------------------------------------
base = Path(__file__).resolve().parents[1]      # project root
data = base / "data"
sys.path.append(str(base))

from setup import portofolio, ticker_currency   # single source of truth

# ---------------------------------------------------------------------
# 1.  Load latest prices & build today’s position vector
# ---------------------------------------------------------------------
px  = pd.read_csv(data / "prices.csv",
                  index_col="date", parse_dates=True).sort_index()
prices_today  = px.iloc[-1]
portfolio_qty = pd.Series(portofolio).astype(float)          # shares / contracts
pos_today     = portfolio_qty * prices_today                 # USD values
NAV           = pos_today.sum()

# ---------------------------------------------------------------------
# 2.  Helper – re-value book under % price shocks
# ---------------------------------------------------------------------
def run_scenario(shock_dict, prices, qty):
    """
    shock_dict : {ticker: pct_move}, e.g. {'AAPL': -0.3}
    prices     : Series of today's prices
    qty        : Series of positions (same index)
    Returns (abs_P/L, pct_P/L) under the shocked market.
    """
    shocked = prices.copy()
    for tkr, pct in shock_dict.items():
        if tkr in shocked.index:
            shocked[tkr] *= (1.0 + pct)
        else:
            # fallback: ignore or log
            print(f"⚠ {tkr} not in price table; shock ignored")

    pl_abs = (qty * shocked).sum() - (qty * prices).sum()
    return pl_abs, pl_abs / NAV

# ---------------------------------------------------------------------
# 3.  Define three scenarios (feel free to extend)
# ---------------------------------------------------------------------
SCENARIOS = {

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

# ---------------------------------------------------------------------
# 4.  Run all scenarios
# ---------------------------------------------------------------------
results = []
for name, shock in SCENARIOS.items():
    abs_pl, pct_pl = run_scenario(shock, prices_today, portfolio_qty)
    results.append({"Scenario": name,
                    "P/L_$":    abs_pl,
                    "P/L_%":    pct_pl})

stress_df = pd.DataFrame(results).set_index("Scenario")

# ---------------------------------------------------------------------
# 5.  Write to Excel (own workbook or add to risk_dashboard.xlsx)
# ---------------------------------------------------------------------
out_path = data / "stress_dashboard.xlsx"
with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    stress_df.to_excel(writer, sheet_name="Stress", float_format="%.4f")

print("✓ stress_dashboard.xlsx written →", out_path.resolve())
