import numpy as np
import pandas as pd
from pathlib import Path
from setup import portofolio, beta_map  # user‑maintained dicts

# Parameters (modifiable)
data_dir   = Path(__file__).resolve().parents[0]/"data"
vol_window = (20, 60, 120)        # trading‑day windows
beta_window= 60                   # for rolling β
cov_scale  = 252                  # daily → annual
alpha = 0.99                 # VaR / ES level (z≈2.326)

data_dir.mkdir(exist_ok=True)

# Load prices & returns
prices = (
    pd.read_csv(data_dir / "prices.csv",
                index_col="date", parse_dates=True)
      .sort_index()
)
returns = prices.pct_change().dropna()

# 1. Rolling volatility (annualised today)
vol_tabs = {}
for w in vol_window:
    vol_ann = returns.rolling(w).std().iloc[-1] * np.sqrt(cov_scale)
    vol_tabs[f"vol{w}"] = vol_ann.to_frame(name="vol_ann")
vol_long = (
    pd.concat(vol_tabs, names=["window"])
      .reset_index()                        # window, asset, vol_ann
)
vol_long["window"] = (
    vol_long["window"].str.extract(r"(\d+)", expand=False).astype(int)
)
vol_long.to_csv(data_dir/"vol_long.csv", index=False)

# 2. Rolling β against chosen benchmarks
def last_beta(asset: str, bench: str, window: int = beta_window) -> float:
    cov = returns[asset].rolling(window).cov(returns[bench])
    var = returns[bench].rolling(window).var()
    return (cov / var).iloc[-1]

beta_tab = pd.Series(
    {a: last_beta(a, b) for a, b in beta_map.items()},
    name=f"beta{beta_window}"
).to_frame()

beta_long = beta_tab.reset_index().rename(columns={"index": "asset"})
beta_long.to_csv(data_dir/"beta_long.csv", index=False)

# 3. Covariance & correlation (annualised)
cov_mat  = returns.cov() * cov_scale
corr_mat = returns.corr()

cov_long = (
    cov_mat.stack()
           .reset_index()
           .rename(columns={"level_0": "asset_i", "level_1": "asset_j", 0: "cov_ann"})
)
cov_long.to_csv(data_dir / "cov_long.csv", index=False)

corr_long = (
    corr_mat.stack()
             .reset_index()
             .rename(columns={"level_0": "asset_i", "level_1": "asset_j", 0: "corr"})
)
corr_long.to_csv(data_dir / "corr_long.csv", index=False)

# 4. Portfolio weights, exposures & Delta‑normal VaR
px_today   = prices.iloc[-1]
pos_value  = pd.Series(portofolio) * px_today  # align by index
nav        = pos_value.sum()
weights    = pos_value / nav

exposure_long = (
    pd.DataFrame({
        "asset": pos_value.index,
        "position_value": pos_value.values,
        "weight": weights.values,
    })
)
exposure_long.to_csv(data_dir / "exposure.csv", index=False)

sigma_p_a  = np.sqrt(weights.T @ cov_mat @ weights)
z          = 2.326  # hard‑code for 99 %
var_99     = -z * sigma_p_a * nav        # negative loss number
var_tab    = pd.DataFrame({
    "NAV": [nav],
    "ann_sigma": [sigma_p_a],
    "VaR_99": [var_99],
})

print("Metrics written to long CSVs")
