import pandas as pd
import numpy as np
import xlsxwriter
from pathlib import Path
from setup import portofolio, ticker_currency, HKD_USD, JPY_USD

# ------------------ PARAMETERS ------------------
LOOKBACK = 250       # days for rolling window
ALPHA    = 0.99      # confidence level
LAMBDA   = 0.94      # EWMA decay

BASE_DIR = Path(__file__).resolve().parents[0]
DATA_DIR = BASE_DIR / "data"
OUT_PATH = DATA_DIR / "var_dashboard.xlsx"
# -------------------------------------------------

# 1. Load price history ----------------------------------------
prices = (pd.read_csv(DATA_DIR / "prices.csv", index_col="date", parse_dates=True)
          .sort_index())
prices.columns = prices.columns.str.strip().str.lstrip('\ufeff')
prices = prices[[t for t in prices.columns if t in portofolio]]

# 2. Compute USD‑based portfolio weights -----------------------
fx_rates = {"HKD": HKD_USD, "JPY": JPY_USD}

def compute_weights(latest_prices: pd.Series) -> dict[str, float]:
    """Return a dict of {ticker: weight} that sums to 1."""
    usd_prices = {}
    for ticker, qty in portofolio.items():
        price = float(latest_prices.get(ticker, np.nan))
        ccy   = ticker_currency.get(ticker, "USD")
        if ccy == "HKD":
            price *= fx_rates["HKD"]
        elif ccy == "JPY":
            price *= fx_rates["JPY"]
        usd_prices[ticker] = price

    pos_val = {t: qty * usd_prices[t] for t, qty in portofolio.items()}
    total   = sum(pos_val.values())
    return {t: v / total for t, v in pos_val.items()}

weights = compute_weights(prices.iloc[-1])

# 3. Portfolio daily returns -----------------------------------
returns = prices.pct_change().dropna()
w_vec   = np.array([weights.get(t, 0.0) for t in prices.columns])
returns["portfolio"] = returns.values @ w_vec

# 4. EWMA volatility -------------------------------------------
port = returns["portfolio"].to_numpy()
n    = len(port)
sigma = np.empty(n)
sigma[0] = np.std(port[:20])
for t in range(1, n):
    sigma[t] = np.sqrt(LAMBDA * sigma[t-1]**2 + (1 - LAMBDA) * port[t-1]**2)

# 5. Rolling HS / FHS VaR & ES (all NEGATIVE) ------------------
hs_var  = np.full(n, np.nan)
fhs_var = np.full(n, np.nan)
hs_es   = np.full(n, np.nan)
fhs_es  = np.full(n, np.nan)

for i in range(LOOKBACK, n):
    window = port[i-LOOKBACK:i]

    # Historical VaR & ES
    q = np.quantile(window, 1 - ALPHA)
    hs_var[i] = q                      # q is already negative
    hs_es[i]  = window[window <= q].mean()

    # Filtered Historical VaR & ES
    z_window = window / sigma[i-LOOKBACK:i]
    z_q = np.quantile(z_window, 1 - ALPHA)
    fhs_var[i] = z_q * sigma[i]
    fhs_es[i]  = z_window[z_window <= z_q].mean() * sigma[i]

# 6. Attach risk series ----------------------------------------
returns["hs_var"]  = hs_var
returns["fhs_var"] = fhs_var
returns["hs_es"]   = hs_es
returns["fhs_es"]  = fhs_es

# 7. Breaches & rolling counts ---------------------------------
returns["breach_hs"]  = (returns["portfolio"] < returns["hs_var"]).astype(int)
returns["breach_fhs"] = (returns["portfolio"] < returns["fhs_var"]).astype(int)
returns["n_breach_hs"]  = returns["breach_hs"].rolling(LOOKBACK).sum()
returns["n_breach_fhs"] = returns["breach_fhs"].rolling(LOOKBACK).sum()

# 8. Back‑test status (today) ----------------------------------
today = returns.index[-1]

def traffic_light(count: int) -> str:
    return "Green" if count <= 4 else ("Amber" if count <= 9 else "Red")

status_df = pd.DataFrame({
    "Model": ["HS", "FHS"],
    "Breach_250d": [int(returns.at[today, "n_breach_hs"]),
                     int(returns.at[today, "n_breach_fhs"])],
    "Traffic_Light": [traffic_light(int(returns.at[today, "n_breach_hs"])),
                       traffic_light(int(returns.at[today, "n_breach_fhs"]))]
})

var_es_today = returns[["portfolio", "hs_var", "fhs_var", "hs_es", "fhs_es"]].dropna()
var_es_today.reset_index().to_csv(DATA_DIR / "var_es_long.csv", index=False)

# 9. Write Excel dashboard -------------------------------------
with pd.ExcelWriter(OUT_PATH, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
    # --- VaR & ES sheet —--------------------------------------
    ts_cols = ["portfolio", "hs_var", "fhs_var", "hs_es", "fhs_es"]
    ts = returns[ts_cols].dropna()
    ts.to_excel(writer, sheet_name="VaR", index_label="Date")

    wb = writer.book
    ws = writer.sheets["VaR"]
    max_row = len(ts) + 1

    chart = wb.add_chart({"type": "line"})
    names   = ["Portfolio Return", "HS VaR (99%)", "FHS VaR (99%)"]
    colours = ["blue", "red", "green"]

    for idx, (name, colour) in enumerate(zip(names, colours)):
        col_letter = chr(66 + idx)  # Column B == 66 in ASCII
        chart.add_series({
            "name": name,
            "categories": f"=VaR!$A$2:$A${max_row}",
            "values":     f"=VaR!${col_letter}$2:${col_letter}${max_row}",
            "line": {"color": colour, "dash_type": "dash"} if idx else {"color": colour}
        })

    chart.set_title({"name": "Portfolio P/L vs. 99 % VaR & ES"})
    chart.set_x_axis({"name": "Date", "date_axis": True})
    chart.set_y_axis({"name": "Return / Risk"})
    chart.set_legend({"position": "top"})
    ws.insert_chart("H2", chart, {"x_scale": 2, "y_scale": 1.3})

    # --- Exceptions sheet -------------------------------------
    exc = returns[["breach_hs", "breach_fhs"]].dropna()
    exc.to_excel(writer, sheet_name="Exceptions", index_label="Date")
    ws_exc = writer.sheets["Exceptions"]
    red_fmt = wb.add_format({"bg_color": "#FFC7CE"})
    ws_exc.conditional_format(f"B2:C{len(exc) + 1}", {
        "type": "cell", "criteria": "==", "value": 1, "format": red_fmt
    })

    # --- Back‑test Status sheet -------------------------------
    status_df.to_excel(writer, sheet_name="Backtest_Status", index=False)
    ws_bt = writer.sheets["Backtest_Status"]

    palette = {"Green": "#C6EFCE", "Amber": "#FFEB9C", "Red": "#FFC7CE"}
    for colour, hexcode in palette.items():
        ws_bt.conditional_format("C2:C3", {
            "type": "text", "criteria": "containing", "value": colour,
            "format": wb.add_format({"bg_color": hexcode})
        })

    bar = wb.add_chart({"type": "column"})
    bar.add_series({
        "name": "250‑day Breaches",
        "categories": "=Backtest_Status!$A$2:$A$3",
        "values":     "=Backtest_Status!$B$2:$B$3",
        "gap": 30
    })
    bar.set_title({"name": f"Back‑test Status {today:%Y-%m-%d}"})
    bar.set_y_axis({"major_gridlines": {"visible": False}})
    ws_bt.insert_chart("E2", bar)

print(f"Dashboard saved → {OUT_PATH.resolve()}")
