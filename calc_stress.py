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

try:
    base = Path(__file__).resolve().parents[0]
except NameError:
    base = Path.cwd()   # project root
data = base/"data"
sys.path.append(str(base))

from setup import portofolio, ticker_currency, scenarios   # single source of truth

px  = pd.read_csv(data/"prices.csv",
                  index_col="date", parse_dates=True).sort_index()
prices_today  = px.iloc[-1]
portfolio_qty = pd.Series(portofolio).astype(float)          # shares / contracts
pos_today     = portfolio_qty * prices_today                 # USD values
NAV           = pos_today.sum()

# Function to re-value book under % price shocks
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

# Run all scenarios
results = []
for name, shock in scenarios.items():
    abs_pl, pct_pl = run_scenario(shock, prices_today, portfolio_qty)
    results.append({"Scenario": name,
                    "P/L_$":    abs_pl,
                    "P/L_%":    pct_pl})

stress_df = pd.DataFrame(results).set_index("Scenario")

stress_df.to_csv(data/"stress_testing.csv", float_format="%.4f")

# Write to Excel (own workbook or add to risk_dashboard.xlsx)
out_path = data/"stress_dashboard.xlsx"
with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    stress_df.to_excel(writer, sheet_name="Stress", float_format="%.4f")

print("✓ stress_dashboard.xlsx written →", out_path.resolve())
