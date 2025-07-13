import pandas as pd
import numpy as np
from pathlib import Path
from setup import portofolio, ticker_currency, HKD_USD, JPY_USD

# Parameters
data_dir   = Path(__file__).resolve().parents[0] / "data"
lookback = 250       # days for rolling window
alpha    = 0.99      # confidence level
decay   = 0.94      # EWMA decay

# Load price history
prices = (pd.read_csv(data_dir/"prices.csv", 
                      index_col="date", parse_dates=True)
          .sort_index()
)

# 1. Compute USD‑based portfolio weights
fx_rates = {"HKD": HKD_USD, "JPY": JPY_USD}

def compute_weights(latest_prices: pd.Series) -> dict[str, float]:
    "Return a dict of {ticker: weight} that sums to 1."
    usd_prices = {}
    for ticker, qty in portofolio.items():
        price = float(latest_prices.get(ticker, np.nan))
        ccy   = ticker_currency.get(ticker, "USD")
        if ccy == "HKD":
            price *= fx_rates["HKD"]
        elif ccy == "JPY":
            price *= fx_rates["JPY"]
        usd_prices[ticker] = price

    pos_val = {tkr: qty * usd_prices[tkr] for tkr, qty in portofolio.items()}
    total   = sum(pos_val.values())
    return {tkr: pos / total for tkr, pos in pos_val.items()}

weights = compute_weights(prices.iloc[-1])

# 2. Portfolio daily returns
returns     = prices.pct_change().dropna()
w_vector    = np.array([weights.get(tkr, 0.0) for tkr in prices.columns])
returns["portfolio"] = returns.values @ w_vector

# 3. EWMA volatility
port        = returns["portfolio"].to_numpy()
n           = len(port)
sigma       = np.empty(n)
sigma[0]    = np.std(port[:20])
for t in range(1, n):
    sigma[t]  = np.sqrt(decay * sigma[t-1]**2 + (1 - decay) * port[t-1]**2)

# 4. Rolling HS / FHS VaR & ES (all negative values)
hs_var  = np.full(n, np.nan)
fhs_var = np.full(n, np.nan)
hs_es   = np.full(n, np.nan)
fhs_es  = np.full(n, np.nan)

for i in range(lookback, n):
    window = port[i-lookback:i]

    # Historical VaR & ES
    q           = np.quantile(window, 1 - alpha)
    hs_var[i]   = q                      # q is already negative
    hs_es[i]    = window[window <= q].mean()

    # Filtered Historical VaR & ES
    z_window    = window / sigma[i-lookback:i]
    z_q         = np.quantile(z_window, 1 - alpha)
    fhs_var[i]  = z_q * sigma[i]
    fhs_es[i]   = z_window[z_window <= z_q].mean() * sigma[i]

# 5. Attach risk series ----------------------------------------
returns["hs_var"]  = hs_var
returns["fhs_var"] = fhs_var
returns["hs_es"]   = hs_es
returns["fhs_es"]  = fhs_es

# 6. Breaches & rolling counts ---------------------------------
returns["breach_hs"]  = (returns["portfolio"] < returns["hs_var"]).astype(int)
returns["breach_fhs"] = (returns["portfolio"] < returns["fhs_var"]).astype(int)
returns["n_breach_hs"]  = returns["breach_hs"].rolling(lookback).sum()
returns["n_breach_fhs"] = returns["breach_fhs"].rolling(lookback).sum()

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
var_es_today.reset_index().to_csv(data_dir/"var_es_long.csv", index=False)

print("VaR & ES saved to var_es_long.CSV")
